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
from datetime import datetime


def health_check(request):
    """Simple health check endpoint for Render."""
    return HttpResponse("OK", status=200)


def home(request):
    """Main view - Step-by-step DeepSearch workflow."""
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
                    request.session["loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
            
            # Handle viewing examples and moving to rules
            elif "view_examples_done" in request.POST:
                # User has reviewed examples, generate rules
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
                
                # Check if all rules processed
                deployed_rules = request.session.get("deployed_rules", [])
                rejected_rules = request.session.get("rejected_rules", [])
                total_rules = len(generated_rules) if generated_rules else 0
                
                if total_rules > 0 and len(deployed_rules) + len(rejected_rules) >= total_rules:
                    # All done, reset
                    request.session["user_issue"] = None
                    request.session["current_example_index"] = -2
                    request.session["deployed_rules"] = []
                    request.session["rejected_rules"] = []
                    request.session["generated_examples"] = None
                    request.session["generated_rules"] = None
                    request.session.modified = True
                    return redirect("home")
                
                return redirect("home")
            
            # Handle rejecting a rule
            elif "reject_rule" in request.POST:
                rule_id = request.POST.get("reject_rule")
                if "rejected_rules" not in request.session:
                    request.session["rejected_rules"] = []
                if rule_id not in request.session["rejected_rules"]:
                    request.session["rejected_rules"].append(rule_id)
                request.session.modified = True
                
                # Check if all rules processed
                deployed_rules = request.session.get("deployed_rules", [])
                rejected_rules = request.session.get("rejected_rules", [])
                total_rules = len(generated_rules) if generated_rules else 0
                
                if total_rules > 0 and len(deployed_rules) + len(rejected_rules) >= total_rules:
                    # All done, reset
                    request.session["user_issue"] = None
                    request.session["current_example_index"] = -2
                    request.session["deployed_rules"] = []
                    request.session["rejected_rules"] = []
                    request.session["generated_examples"] = None
                    request.session["generated_rules"] = None
                    request.session.modified = True
                    return redirect("home")
                
                return redirect("home")
        
        # Determine current step
        step = "issue_input"
        
        print(f"DEBUG: Step determination - is_searching={is_searching}, is_generating_rules={is_generating_rules}, current_index={current_index}")
        
        # Check if searching (loading examples)
        if is_searching and current_index == -1:
            step = "searching"
            loading_screen_shown = request.session.get("loading_screen_shown", False)
            if not loading_screen_shown:
                request.session["loading_screen_shown"] = True
                request.session.modified = True
            elif generated_examples is None and user_issue:
                # Generate examples from WildChat
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
                # Generate rules from examples
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
            "is_searching": is_searching,
            "is_generating_rules": is_generating_rules,
            "total_rules": total_rules,
        }
        
        return render(request, "commander/home.html", context)
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        sys.stderr.write(f"ERROR IN HOME VIEW: {e}\n")
        sys.stderr.write(error_traceback)
        sys.stderr.flush()
        
        error_html = f"""<html>
<head>
    <title>Error - RainDrop Commander</title>
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
