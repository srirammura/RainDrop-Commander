from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from .forms import RuleAuditForm
from .services.commander_agent import CommanderAgent
from .services.deepsearch_generator import (
    generate_examples_from_issue,
    generate_suggested_rules_from_examples,
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
    """Main view - Step-by-step DeepSearch workflow with Commander."""
    import sys
    import traceback
    
    # Handle HEAD requests (health checks) quickly
    if request.method == "HEAD":
        sys.stderr.write("DEBUG: HEAD request received, returning 200\n")
        sys.stderr.flush()
        return HttpResponse(status=200)
    
    # Force output to stderr (which Render captures) immediately
    sys.stderr.write("DEBUG: home() view called\n")
    sys.stderr.flush()
    
    try:
        sys.stderr.write("DEBUG: Getting common issues\n")
        sys.stderr.flush()
        # Get common issues
        common_issues = get_common_issues()
        sys.stderr.write(f"DEBUG: Got {len(common_issues)} common issues\n")
        sys.stderr.flush()
        
        # Initialize session variables
        if "example_labels" not in request.session:
            request.session["example_labels"] = {}
        if "current_example_index" not in request.session:
            request.session["current_example_index"] = -2
        if "current_rule_index" not in request.session:
            request.session["current_rule_index"] = 0
        if "deployed_rules" not in request.session:
            request.session["deployed_rules"] = []
        if "rejected_rules" not in request.session:
            request.session["rejected_rules"] = []
        
        # Get session data
        user_issue = request.session.get("user_issue")
        example_labels = request.session.get("example_labels", {})
        current_index = request.session.get("current_example_index", -2)
        current_rule_index = request.session.get("current_rule_index", 0)
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
        
        # Always get fresh suggested_rules from generated_rules
        suggested_rules = generated_rules if generated_rules else []
        
        total_examples = len(deepsearch_issue["examples"]) if deepsearch_issue else 0
        
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
                    request.session["example_labels"] = {}
                    request.session["loading_screen_shown"] = False
                    request.session.modified = True
                    return redirect("home")
            
            # Handle marking an example
            elif "mark_example" in request.POST:
                example_index = int(request.POST.get("example_index"))
                label = request.POST.get("label")
                
                # Get fresh examples from session
                examples_to_use = request.session.get("generated_examples")
                if not examples_to_use:
                    print(f"ERROR: No generated_examples in session when marking example {example_index}")
                    request.session["error_message"] = "Examples not found. Please start over."
                    request.session["user_issue"] = None
                    request.session["current_example_index"] = -2
                    request.session.modified = True
                    return redirect("home")
                
                total_examples = len(examples_to_use)
                
                example_labels[str(example_index)] = label
                request.session["example_labels"] = example_labels
                request.session.modified = True
                
                if example_index < total_examples - 1:
                    request.session["current_example_index"] = example_index + 1
                    request.session.modified = True
                    return redirect("home")
                else:
                    # All examples labeled, prepare for rules generation
                    labeled_examples_list = []
                    for i, ex in enumerate(examples_to_use):
                        label = example_labels.get(str(i), "MATCH")
                        labeled_examples_list.append({
                            "user": ex.get("user", ""),
                            "assistant": ex.get("assistant", ""),
                            "user_label": label,
                        })
                    
                    print(f"DEBUG: All {total_examples} examples labeled. Setting up rules generation.")
                    request.session["generating_rules"] = True
                    request.session["current_example_index"] = -3
                    request.session["generated_rules"] = None
                    request.session["pending_labeled_examples"] = labeled_examples_list
                    request.session["rules_loading_screen_shown"] = False
                    request.session.modified = True
                    print(f"DEBUG: Session set - generating_rules=True, current_index=-3")
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
                
                # Stay on the same page to show all rules
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
                
                # Stay on the same page to show all rules
                return redirect("home")
        
        # Determine current step
        step = "issue_input"
        current_example = None
        
        print(f"DEBUG: Step determination - is_searching={is_searching}, is_generating_rules={is_generating_rules}, current_index={current_index}, user_issue={user_issue is not None}, generated_examples={generated_examples is not None}")
        
        try:
            # Check if searching (loading examples)
            if is_searching and current_index == -1:
                step = "searching"
                loading_screen_shown = request.session.get("loading_screen_shown", False)
                if not loading_screen_shown:
                    request.session["loading_screen_shown"] = True
                    request.session.modified = True
                elif generated_examples is None and user_issue:
                    # Generate examples
                    try:
                        examples = generate_examples_from_issue(user_issue)
                        request.session["generated_examples"] = examples
                        request.session["searching"] = False
                        request.session["current_example_index"] = 0
                        request.session["loading_screen_shown"] = False
                        request.session.modified = True
                        return redirect("home")
                    except Exception as e:
                        print(f"ERROR: Failed to generate examples: {e}")
                        import traceback
                        traceback.print_exc()
                        request.session["user_issue"] = None
                        request.session["current_example_index"] = -2
                        request.session["searching"] = False
                        request.session.modified = True
                        return redirect("home")
            
            # Check if generating rules
            elif is_generating_rules and current_index == -3:
                print(f"DEBUG: Detected rules generation step - is_generating_rules={is_generating_rules}, current_index={current_index}")
                step = "generating_rules"
                rules_loading_screen_shown = request.session.get("rules_loading_screen_shown", False)
                if not rules_loading_screen_shown:
                    # First time showing loading screen, set flag
                    request.session["rules_loading_screen_shown"] = True
                    request.session.modified = True
                    print(f"DEBUG: First time showing rules loading screen")
                elif generated_rules is None and user_issue:
                    # Loading screen already shown, now generate rules
                    pending_labeled_examples = request.session.get("pending_labeled_examples")
                    print(f"DEBUG: About to generate rules. pending_labeled_examples: {pending_labeled_examples is not None}")
                    if pending_labeled_examples:
                        try:
                            print(f"DEBUG: ===== CALLING LLM TO GENERATE RULES =====")
                            rules = generate_suggested_rules_from_examples(user_issue, pending_labeled_examples)
                            print(f"DEBUG: ===== LLM GENERATED {len(rules)} RULES =====")
                            request.session["generated_rules"] = rules
                            request.session["generating_rules"] = False
                            request.session["current_example_index"] = -1
                            request.session["pending_labeled_examples"] = None
                            request.session["rules_loading_screen_shown"] = False
                            request.session["current_rule_index"] = 0
                            request.session.modified = True
                            print(f"DEBUG: Rules generated, redirecting to rules review")
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
                    else:
                        print(f"ERROR: No pending_labeled_examples found")
                        request.session["user_issue"] = None
                        request.session["current_example_index"] = -2
                        request.session["generating_rules"] = False
                        request.session.modified = True
                        return redirect("home")
            
            # Show labeling step
            elif current_index >= 0 and generated_examples and user_issue:
                step = "labeling_examples"
                if deepsearch_issue and deepsearch_issue.get("examples") and current_index < len(deepsearch_issue["examples"]):
                    current_example = deepsearch_issue["examples"][current_index]
            
            # Show rules review
            elif current_index == -1:
                # Get fresh generated_rules from session
                generated_rules = request.session.get("generated_rules")
                if generated_rules and len(generated_rules) > 0:
                    # Rebuild suggested_rules from generated_rules to ensure it's up to date
                    suggested_rules = generated_rules
                    step = "rules_review"
                    print(f"DEBUG: Showing rules review - {len(suggested_rules)} rules available")
                else:
                    # No rules yet, might still be generating
                    if is_generating_rules:
                        step = "generating_rules"
                    else:
                        step = "issue_input"
        except Exception as step_error:
            print(f"ERROR in step determination: {step_error}")
            import traceback
            traceback.print_exc()
            step = "issue_input"  # Fallback to safe state
        
        # Build labeled examples and audit rules
        if step == "rules_review":
            # Ensure deepsearch_issue is built if we have examples
            if not deepsearch_issue and user_issue and generated_examples:
                deepsearch_issue = {
                    "description": user_issue,
                    "examples": generated_examples,
                }
            
            labeled_examples = []
            if deepsearch_issue and deepsearch_issue.get("examples"):
                for i, ex in enumerate(deepsearch_issue["examples"]):
                    label = example_labels.get(str(i), "MATCH")
                    labeled_examples.append({
                        "text": f"User: {ex['user']}\nAssistant: {ex['assistant']}",
                        "label": label,
                    })
            
            # Audit rules
            # Ensure suggested_rules is a list
            if not isinstance(suggested_rules, list):
                suggested_rules = []
            for rule in suggested_rules:
                if rule.get("status") != "audited":
                    examples_for_audit = labeled_examples.copy()
                    examples_for_audit.append({
                        "text": rule.get("example", ""),
                        "label": "MATCH",
                    })
                    try:
                        commander = CommanderAgent(rule.get("description", ""), examples_for_audit)
                        audit_result = commander.audit_rule()
                        rule["audit_result"] = audit_result
                        rule["audit_result_json"] = json.dumps(audit_result, cls=DjangoJSONEncoder, default=str)
                        rule["status"] = "audited"
                    except Exception as e:
                        rule["audit_error"] = str(e)
                        rule["status"] = "error"
        
        # Mark deployed and rejected rules
        deployed_rules = request.session.get("deployed_rules", [])
        rejected_rules = request.session.get("rejected_rules", [])
        # Ensure suggested_rules is always a list
        if not isinstance(suggested_rules, list):
            suggested_rules = []
        for rule in suggested_rules:
            if rule.get("id") in deployed_rules:
                rule["deployed"] = True
            if rule.get("id") in rejected_rules:
                rule["user_rejected"] = True
        
        # Show all non-rejected rules in rules_review
        display_rules = [r for r in suggested_rules if not r.get("user_rejected", False)] if isinstance(suggested_rules, list) else []
        
        # Context - ensure all variables are properly initialized
        display_user_issue = None if step == "issue_input" else user_issue
        
        # Ensure deepsearch_issue is None if not set
        if deepsearch_issue is None:
            deepsearch_issue = None
        
        # Ensure current_example is None if not set
        if current_example is None:
            current_example = None
        
        # Calculate total_rules safely
        total_rules = len([r for r in suggested_rules if isinstance(suggested_rules, list) and not r.get("user_rejected", False)]) if isinstance(suggested_rules, list) else 0
        
        print(f"DEBUG: Building context - step={step}, total_examples={total_examples}, total_rules={total_rules}, display_rules_count={len(display_rules)}")
        
        try:
            sys.stderr.write("DEBUG: Creating context dictionary\n")
            sys.stderr.flush()
            context = {
                "common_issues": common_issues,
                "user_issue": display_user_issue,
                "deepsearch_issue": deepsearch_issue,
                "suggested_rules": display_rules,
                "current_example_index": current_index,
                "current_example": current_example,
                "total_examples": total_examples,
                "example_labels": example_labels if example_labels else {},
                "step": step,
                "progress": (len(example_labels) / total_examples * 100) if total_examples > 0 and example_labels else 0,
                "deployed_rules": deployed_rules if deployed_rules else [],
                "is_searching": is_searching,
                "is_generating_rules": is_generating_rules,
                "total_rules": total_rules,
            }
            sys.stderr.write("DEBUG: Context dictionary created\n")
            sys.stderr.flush()
            
            sys.stderr.write("DEBUG: Context built successfully, attempting to render template\n")
            sys.stderr.flush()
            print(f"DEBUG: Context built successfully, attempting to render template")
            sys.stderr.write("DEBUG: Print statement executed, continuing...\n")
            sys.stderr.flush()
            
            # Reset error count on successful request
            sys.stderr.write("DEBUG: About to update session\n")
            sys.stderr.flush()
            try:
                if "error_count" in request.session:
                    sys.stderr.write("DEBUG: Resetting error_count in session\n")
                    sys.stderr.flush()
                    request.session["error_count"] = 0
                    request.session.modified = True
                sys.stderr.write("DEBUG: Session updated successfully\n")
                sys.stderr.flush()
            except Exception as session_err:
                error_tb = traceback.format_exc()
                sys.stderr.write(f"WARNING: Session update failed: {session_err}\n")
                sys.stderr.write(error_tb)
                sys.stderr.flush()
                # Continue anyway
            
            sys.stderr.write("DEBUG: About to call render()\n")
            sys.stderr.flush()
            try:
                sys.stderr.write("DEBUG: Calling render() now...\n")
                sys.stderr.flush()
                result = render(request, "commander/home.html", context)
                sys.stderr.write("DEBUG: render() completed successfully\n")
                sys.stderr.flush()
                return result
            except Exception as render_exc:
                error_tb = traceback.format_exc()
                sys.stderr.write(f"ERROR: render() raised exception: {render_exc}\n")
                sys.stderr.write(error_tb)
                sys.stderr.flush()
                print(f"ERROR: render() raised exception: {render_exc}")
                traceback.print_exc()
                raise
        except Exception as render_error:
            error_traceback = traceback.format_exc()
            sys.stderr.write("=" * 80 + "\n")
            sys.stderr.write("ERROR IN INNER TRY BLOCK (context/render):\n")
            sys.stderr.write("=" * 80 + "\n")
            sys.stderr.write(f"Exception Type: {type(render_error).__name__}\n")
            sys.stderr.write(f"Exception Message: {str(render_error)}\n")
            sys.stderr.write("\nFull Traceback:\n")
            sys.stderr.write(error_traceback)
            sys.stderr.write("=" * 80 + "\n")
            sys.stderr.flush()
            print(f"ERROR during template rendering: {render_error}")
            traceback.print_exc()
            # Re-raise to be caught by outer exception handler
            raise
    except Exception as e:
        error_traceback = traceback.format_exc()
        # Write to stderr (captured by Render logs)
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("ERROR IN HOME VIEW:\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(f"Exception Type: {type(e).__name__}\n")
        sys.stderr.write(f"Exception Message: {str(e)}\n")
        sys.stderr.write("\nFull Traceback:\n")
        sys.stderr.write(error_traceback)
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        
        # Also print to stdout
        print("=" * 80)
        print("ERROR IN HOME VIEW:")
        print("=" * 80)
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print("\nFull Traceback:")
        print(error_traceback)
        print("=" * 80)
        
        # Log to file as well (handle permission errors in production)
        try:
            with open("/tmp/django_error.log", "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"ERROR at {datetime.now()}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Exception Type: {type(e).__name__}\n")
                f.write(f"Exception Message: {str(e)}\n")
                f.write(f"\nFull Traceback:\n{error_traceback}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as log_error:
            print(f"Could not write to error log: {log_error}")
        
        # Prevent infinite redirect loops
        error_count = request.session.get("error_count", 0)
        sys.stderr.write(f"DEBUG: Error count: {error_count}\n")
        sys.stderr.flush()
        
        if error_count > 2:
            # Too many errors, return a simple error response instead of redirecting
            from django.http import HttpResponse
            sys.stderr.write("DEBUG: Returning error response (too many errors)\n")
            sys.stderr.flush()
            return HttpResponse(
                f"<html><body><h1>Error</h1><p>An error occurred. Please refresh the page.</p><p>Error: {str(e)}</p><pre>{error_traceback}</pre></body></html>",
                status=500
            )
        
        # Reset session to safe state
        try:
            request.session["error_message"] = f"An error occurred: {str(e)}"
            request.session["error_count"] = error_count + 1
            request.session["user_issue"] = None
            request.session["current_example_index"] = -2
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["example_labels"] = {}
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session.modified = True
            sys.stderr.write("DEBUG: Session reset, redirecting\n")
            sys.stderr.flush()
        except Exception as session_error:
            sys.stderr.write(f"ERROR updating session: {session_error}\n")
            sys.stderr.flush()
            # If session update fails, just return error response
            from django.http import HttpResponse
            return HttpResponse(
                f"<html><body><h1>Error</h1><p>An error occurred.</p><p>Error: {str(e)}</p><p>Session Error: {str(session_error)}</p><pre>{error_traceback}</pre></body></html>",
                status=500
            )
        
        # Only redirect if we haven't hit the error limit
        return redirect("home")
