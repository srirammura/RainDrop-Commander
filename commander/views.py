from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from .forms import RuleAuditForm
from .services.deepsearch_generator import (
    generate_examples_from_issue,
    generate_rules_from_examples,
)
from .services.mock_data import (
    get_mock_rule_by_id, 
    get_all_mock_rules,
    get_common_issues,
)
import json
import os
from datetime import datetime


def health_check(request):
    """Simple health check endpoint for Render."""
    return HttpResponse("OK", status=200)


def home(request):
    """Main view - Step-by-step DeepSearch workflow with training and scanning."""
    import sys
    import traceback
    from django.http import HttpResponse
    
    # Handle HEAD requests (health checks) quickly
    if request.method == "HEAD":
        return HttpResponse(status=200)
    
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    # Handle health checks and monitoring requests
    if 'Go-http-client' in user_agent or 'health' in request.path.lower():
        return HttpResponse("OK", status=200)
    
    try:
        # Get common issues
        common_issues = get_common_issues()
        
        # Initialize session variables
        if "current_example_index" not in request.session:
            request.session["current_example_index"] = -2
        if "deployed_rules" not in request.session:
            request.session["deployed_rules"] = []
        if "rejected_rules" not in request.session:
            request.session["rejected_rules"] = []
        
        # Get session data
        user_issue = request.session.get("user_issue")
        current_index = request.session.get("current_example_index", -2)
        generated_examples = request.session.get("generated_examples")
        generated_rules = request.session.get("generated_rules")
        is_searching = request.session.get("searching", False)
        is_generating_rules = request.session.get("generating_rules", False)
        is_training = request.session.get("training", False)
        is_scanning = request.session.get("scanning_production", False)
        training_result = request.session.get("training_result")
        scan_result = request.session.get("scan_result")
        
        # Build deepsearch_issue from generated examples
        if user_issue and generated_examples:
            deepsearch_issue = {
                "description": user_issue,
                "examples": generated_examples,
            }
        else:
            deepsearch_issue = None
        
        suggested_rules = generated_rules if generated_rules else []
        
        # Calculate total_examples
        total_examples = len(generated_examples) if generated_examples else 0
        
        # Handle POST requests
        if request.method == "POST":
            # Handle issue input
            if "submit_issue" in request.POST:
                issue_text = request.POST.get("issue_text", "").strip()
                if issue_text:
                    request.session["user_issue"] = issue_text
                    request.session["searching"] = True
                    request.session["current_example_index"] = -1
                    request.session["generated_examples"] = None
                    request.session["generated_rules"] = None
                    request.session["training_result"] = None
                    request.session["scan_result"] = None
                    request.session["loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
            
            # Handle viewing examples and moving to rules
            elif "view_examples_done" in request.POST:
                if generated_examples and user_issue:
                    request.session["generating_rules"] = True
                    request.session["current_example_index"] = -3
                    request.session["generated_rules"] = None
                    request.session["rules_loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
            
            # Handle deploying a rule
            elif "deploy_rule" in request.POST:
                rule_id = request.POST.get("deploy_rule")
                if "deployed_rules" not in request.session:
                    request.session["deployed_rules"] = []
                if rule_id not in request.session["deployed_rules"]:
                    request.session["deployed_rules"].append(rule_id)
                request.session.modified = True
                return redirect("home")
            
            # Handle rejecting a rule
            elif "reject_rule" in request.POST:
                rule_id = request.POST.get("reject_rule")
                if "rejected_rules" not in request.session:
                    request.session["rejected_rules"] = []
                if rule_id not in request.session["rejected_rules"]:
                    request.session["rejected_rules"].append(rule_id)
                request.session.modified = True
                return redirect("home")
            
            # Handle starting classifier training
            elif "start_training" in request.POST:
                request.session["training"] = True
                request.session["training_loading_shown"] = False
                request.session.modified = True
                return redirect("home")
            
            # Handle starting production scan
            elif "start_scanning" in request.POST:
                request.session["scanning_production"] = True
                request.session["scanning_loading_shown"] = False
                request.session.modified = True
                return redirect("home")
            
            # Handle starting new issue
            elif "new_issue" in request.POST:
                # Reset everything
                request.session["user_issue"] = None
                request.session["current_example_index"] = -2
                request.session["deployed_rules"] = []
                request.session["rejected_rules"] = []
                request.session["generated_examples"] = None
                request.session["generated_rules"] = None
                request.session["training"] = False
                request.session["scanning_production"] = False
                request.session["training_result"] = None
                request.session["scan_result"] = None
                request.session.modified = True
                return redirect("home")
        
        # Determine current step
        step = "issue_input"
        
        print(f"DEBUG: Step determination - is_searching={is_searching}, is_generating_rules={is_generating_rules}, is_training={is_training}, is_scanning={is_scanning}")
        
        # Check if searching (loading examples)
        if is_searching and current_index == -1:
            step = "searching"
            loading_screen_shown = request.session.get("loading_screen_shown", False)
            if not loading_screen_shown:
                request.session["loading_screen_shown"] = True
                request.session.modified = True
            elif generated_examples is None and user_issue:
                try:
                    print(f"DEBUG: Starting example sampling for issue: '{user_issue[:50]}...'")
                    examples = generate_examples_from_issue(user_issue)
                    print(f"DEBUG: Example sampling completed. Got {len(examples)} examples")
                    request.session["generated_examples"] = examples
                    request.session["searching"] = False
                    request.session["current_example_index"] = 0
                    request.session["loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
                except Exception as e:
                    print(f"ERROR: Failed to sample examples: {e}")
                    import traceback
                    traceback.print_exc()
                    request.session["user_issue"] = None
                    request.session["current_example_index"] = -2
                    request.session["searching"] = False
                    request.session["error_message"] = f"Failed to find examples: {str(e)}"
                    request.session.modified = True
                    return redirect("home")
        
        # Check if generating rules
        elif is_generating_rules and current_index == -3:
            step = "generating_rules"
            rules_loading_screen_shown = request.session.get("rules_loading_screen_shown", False)
            if not rules_loading_screen_shown:
                request.session["rules_loading_screen_shown"] = True
                request.session.modified = True
            elif generated_rules is None and user_issue and generated_examples:
                try:
                    print(f"DEBUG: Generating rules from {len(generated_examples)} examples")
                    rules = generate_rules_from_examples(user_issue, generated_examples)
                    print(f"DEBUG: Generated {len(rules)} rules")
                    request.session["generated_rules"] = rules
                    request.session["generating_rules"] = False
                    request.session["current_example_index"] = -1
                    request.session["rules_loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
                except Exception as e:
                    print(f"ERROR: Failed to generate rules: {e}")
                    import traceback
                    traceback.print_exc()
                    request.session["user_issue"] = None
                    request.session["current_example_index"] = -2
                    request.session["generating_rules"] = False
                    request.session.modified = True
                    return redirect("home")
        
        # Check if training classifier
        elif is_training and not training_result:
            step = "training_classifier"
            training_loading_shown = request.session.get("training_loading_shown", False)
            if not training_loading_shown:
                request.session["training_loading_shown"] = True
                request.session.modified = True
            else:
                # Run training
                try:
                    from .services.training_data_generator import generate_full_training_dataset, save_dataset_to_huggingface_format
                    from .services.classifier_trainer import train_classifier
                    import hashlib
                    
                    # Get deployed rules
                    deployed_rules = request.session.get("deployed_rules", [])
                    accepted_rules = [r for r in generated_rules if r.get("id") in deployed_rules]
                    
                    if not accepted_rules:
                        accepted_rules = generated_rules[:2]  # Use first 2 if none deployed
                    
                    print(f"DEBUG: Training classifier with {len(accepted_rules)} rules")
                    
                    # Generate training data
                    issue_hash = hashlib.md5(user_issue.encode('utf-8')).hexdigest()[:8]
                    dataset = generate_full_training_dataset(
                        rules=accepted_rules,
                        issue_description=user_issue,
                        examples_per_rule=30  # Reduced for demo
                    )
                    
                    # Save dataset
                    dataset_dir = f"/tmp/raindrop_dataset_{issue_hash}"
                    save_dataset_to_huggingface_format(dataset, dataset_dir)
                    
                    # Train classifier
                    model_dir = f"/tmp/raindrop_model_{issue_hash}"
                    result = train_classifier(
                        dataset=dataset,
                        model_output_dir=model_dir,
                        epochs=2,  # Reduced for demo
                        batch_size=8
                    )
                    
                    request.session["training_result"] = {
                        "model_path": model_dir,
                        "metrics": result["metrics"],
                        "train_size": dataset["metadata"]["total_positive"] + dataset["metadata"]["total_negative"],
                        "accuracy": round(result["metrics"].get("eval_accuracy", 0) * 100, 1),
                        "f1": round(result["metrics"].get("eval_f1", 0) * 100, 1)
                    }
                    request.session["training"] = False
                    request.session["training_loading_shown"] = False
                    request.session.modified = True
                    return redirect("home")
                    
                except Exception as e:
                    print(f"ERROR: Training failed: {e}")
                    import traceback
                    traceback.print_exc()
                    request.session["training_result"] = {"error": str(e)}
                    request.session["training"] = False
                    request.session.modified = True
                    return redirect("home")
        
        # Check if scanning production
        elif is_scanning and not scan_result:
            step = "scanning_production"
            scanning_loading_shown = request.session.get("scanning_loading_shown", False)
            if not scanning_loading_shown:
                request.session["scanning_loading_shown"] = True
                request.session.modified = True
            else:
                # Run scan
                try:
                    from .services.scanner_service import scan_wildchat_with_classifier, get_scan_statistics
                    
                    model_path = training_result.get("model_path")
                    if not model_path:
                        raise Exception("No trained model found")
                    
                    print(f"DEBUG: Starting production scan with model: {model_path}")
                    
                    results = scan_wildchat_with_classifier(
                        model_dir=model_path,
                        issue_description=user_issue,
                        num_samples=5000,  # Scan 5K for demo
                        batch_size=32,
                        confidence_threshold=0.7
                    )
                    
                    stats = get_scan_statistics(results)
                    
                    request.session["scan_result"] = {
                        "total_scanned": results["total_scanned"],
                        "total_flagged": results["total_flagged"],
                        "issue_rate": results["issue_rate_percent"],
                        "scan_rate": results["scan_rate_per_second"],
                        "duration": results["scan_duration_seconds"],
                        "flagged_issues": results["flagged_issues"][:20],  # Top 20
                        "statistics": stats
                    }
                    request.session["scanning_production"] = False
                    request.session["scanning_loading_shown"] = False
                    request.session.modified = True
                    return redirect("home")
                    
                except Exception as e:
                    print(f"ERROR: Scanning failed: {e}")
                    import traceback
                    traceback.print_exc()
                    request.session["scan_result"] = {"error": str(e)}
                    request.session["scanning_production"] = False
                    request.session.modified = True
                    return redirect("home")
        
        # Show scan results
        elif scan_result and not scan_result.get("error"):
            step = "scan_results"
        
        # Show training results
        elif training_result and not training_result.get("error"):
            step = "training_complete"
        
        # Show examples review
        elif current_index >= 0 and generated_examples and user_issue:
            step = "viewing_examples"
        
        # Show rules review
        elif current_index == -1:
            generated_rules = request.session.get("generated_rules")
            if generated_rules and len(generated_rules) > 0:
                suggested_rules = generated_rules
                step = "rules_review"
            else:
                if is_generating_rules:
                    step = "generating_rules"
                else:
                    step = "issue_input"
        
        # Mark deployed and rejected rules
        deployed_rules = request.session.get("deployed_rules", [])
        rejected_rules = request.session.get("rejected_rules", [])
        
        for i, rule in enumerate(suggested_rules):
            if not isinstance(rule, dict):
                continue
            if "id" not in rule:
                rule["id"] = f"rule_{i}"
            if rule.get("id") in deployed_rules:
                rule["deployed"] = True
            if rule.get("id") in rejected_rules:
                rule["user_rejected"] = True
        
        # Filter out rejected rules for display
        display_rules = [r for r in suggested_rules if isinstance(r, dict) and not r.get("user_rejected", False)]
        
        # Context
        display_user_issue = None if step == "issue_input" else user_issue
        total_rules = len(display_rules)
        num_deployed = len([r for r in display_rules if r.get("deployed")])
        
        print(f"DEBUG: Building context - step={step}, total_examples={total_examples}, total_rules={total_rules}")
        
        context = {
            "common_issues": common_issues,
            "user_issue": display_user_issue,
            "deepsearch_issue": deepsearch_issue,
            "suggested_rules": display_rules,
            "current_example_index": current_index,
            "total_examples": total_examples,
            "step": step,
            "deployed_rules": deployed_rules,
            "num_deployed": num_deployed,
            "is_searching": is_searching,
            "is_generating_rules": is_generating_rules,
            "is_training": is_training,
            "is_scanning": is_scanning,
            "total_rules": total_rules,
            "training_result": training_result,
            "scan_result": scan_result,
        }
        
        return render(request, "commander/home.html", context)
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        sys.stderr.write(f"ERROR IN HOME VIEW: {e}\n")
        sys.stderr.write(error_traceback)
        sys.stderr.flush()
        
        error_html = f"""<html>
<head>
    <title>Error - RainDrop DeepSearch</title>
    <style>
        body {{ font-family: 'Inter', Arial, sans-serif; padding: 40px; background: #1a1a1a; color: #bfdbfe; }}
        h1 {{ color: #ef4444; }}
        a {{ color: #60a5fa; text-decoration: none; }}
        pre {{ background: #0d0d0d; padding: 15px; overflow-x: auto; font-size: 12px; border: 2px solid #60a5fa; }}
    </style>
</head>
<body>
    <h1>Application Error</h1>
    <p>An error occurred. Please try again.</p>
    <p><a href="/">← Return to Homepage</a></p>
    <details>
        <summary>Technical Details</summary>
        <pre>{error_traceback}</pre>
    </details>
</body>
</html>"""
        
        return HttpResponse(error_html, status=500)
