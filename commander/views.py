from django.shortcuts import render, redirect
from django.http import JsonResponse
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


def home(request):
    """Main view - Step-by-step DeepSearch workflow with Commander."""
    # Get common issues
    common_issues = get_common_issues()
    
    # Reset session on GET requests - always start from homepage on fresh page load
    # Use a flag to preserve state during workflow redirects
    session_was_cleared = False
    if request.method == "GET":
        # Check if we're in the middle of a workflow (preserve state during redirects)
        in_workflow = request.session.get("in_workflow", False)
        
        # Always clear user_issue and issue_hash on fresh page load (not in workflow)
        # This ensures no issue is displayed when first entering the homepage
        if not in_workflow or request.GET.get('reset') == '1':
            # Don't use flush() - it can cause issues. Instead, clear individual keys
            request.session["example_labels"] = {}
            request.session["current_example_index"] = -2  # -2 means show issue input
            request.session["user_issue"] = None
            request.session["issue_hash"] = None  # Clear issue hash as well
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["deployed_rules"] = []
            request.session["rejected_rules"] = []
            request.session["loading_screen_shown"] = False
            request.session["rules_loading_screen_shown"] = False
            request.session["pending_labeled_examples"] = None
            request.session["error_message"] = None
            request.session["current_rule_index"] = 0
            request.session["in_workflow"] = False
            request.session.modified = True
            session_was_cleared = True
            print(f"DEBUG: Session cleared on GET request - user_issue and issue_hash set to None")
        
        # Additional safety: If we're not in a workflow and there's a user_issue, clear it
        # This handles edge cases where in_workflow might be incorrectly set
        if not in_workflow and request.session.get("user_issue"):
            print(f"DEBUG: Additional safety check - clearing user_issue even though in_workflow is False")
            request.session["user_issue"] = None
            request.session["issue_hash"] = None
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session.modified = True
            session_was_cleared = True
    
    # If session was just cleared on GET request, skip ALL workflow logic and go straight to issue input
    if session_was_cleared and request.method == "GET":
        print(f"DEBUG: Session was cleared - skipping all workflow logic, going straight to issue_input")
        # Force all variables to initial state
        user_issue = None
        is_searching = False
        is_generating_rules = False
        example_labels = {}
        current_index = -2
        generated_examples = None
        generated_rules = None
        deepsearch_issue = None
        suggested_rules = []
        total_examples = 0
        step = "issue_input"
        current_example = None
    else:
        # Initialize session data (for POST requests or if not already set)
        if "example_labels" not in request.session:
            request.session["example_labels"] = {}
        if "current_example_index" not in request.session:
            request.session["current_example_index"] = -2  # -2 means show issue input
        if "user_issue" not in request.session:
            request.session["user_issue"] = None
        if "searching" not in request.session:
            request.session["searching"] = False
        if "generating_rules" not in request.session:
            request.session["generating_rules"] = False
        if "generated_examples" not in request.session:
            request.session["generated_examples"] = None
        if "generated_rules" not in request.session:
            request.session["generated_rules"] = None
        if "issue_hash" not in request.session:
            request.session["issue_hash"] = None
        if "current_rule_index" not in request.session:
            request.session["current_rule_index"] = 0
        
        user_issue = request.session.get("user_issue")
        is_searching = request.session.get("searching", False)
        is_generating_rules = request.session.get("generating_rules", False)
        example_labels = request.session.get("example_labels", {})
        current_index = request.session.get("current_example_index", -2)
        generated_examples = request.session.get("generated_examples")
        generated_rules = request.session.get("generated_rules")
        stored_issue_hash = request.session.get("issue_hash")
        
        # Calculate hash of current issue to detect changes
        import hashlib
        current_issue_hash = None
        if user_issue:
            current_issue_hash = hashlib.md5(user_issue.encode()).hexdigest()
        
        # If issue changed, clear all generated data and regenerate
        if user_issue and current_issue_hash != stored_issue_hash:
            print(f"DEBUG: Issue changed or first time. Old hash: {stored_issue_hash}, New hash: {current_issue_hash}")
            print(f"DEBUG: Clearing cached examples and rules to force fresh LLM generation")
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["example_labels"] = {}
            request.session["issue_hash"] = current_issue_hash
            generated_examples = None
            generated_rules = None
            # Reset to searching state if we have an issue but no examples
            if current_index not in [-1, -3]:  # Not already in loading state
                request.session["searching"] = True
                request.session["current_example_index"] = -1
                request.session["loading_screen_shown"] = False
                is_searching = True
                current_index = -1
        
        # Check if we have a valid complete workflow
        # Only reset if we have user_issue but no generated_examples (and we're not in loading state)
        # Don't reset if we're in loading state (current_index == -1 or -3) - that's expected
        if user_issue and not generated_examples and current_index not in [-1, -3]:
            # Incomplete workflow detected - clear everything and start fresh
            # But only if we're not in a loading state
            request.session["user_issue"] = None
            request.session["current_example_index"] = -2
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["example_labels"] = {}
            request.session.modified = True
            # Update local variables
            user_issue = None
            current_index = -2
            generated_examples = None
            generated_rules = None
        
        # Build deepsearch_issue from generated examples or use empty
        if user_issue and generated_examples:
            deepsearch_issue = {
                "description": user_issue,
                "examples": generated_examples,
            }
            suggested_rules = generated_rules if generated_rules else []
        else:
            deepsearch_issue = None
            suggested_rules = []
        
        total_examples = len(deepsearch_issue["examples"]) if deepsearch_issue else 0
    
    if request.method == "POST":
        # Handle issue input
        if "submit_issue" in request.POST:
                issue_text = request.POST.get("issue_text", "").strip()
                if issue_text:
                    # Calculate hash for the new issue
                    import hashlib
                    issue_hash = hashlib.md5(issue_text.encode()).hexdigest()
                    
                    # Always clear previous data when submitting a new issue
                    request.session["user_issue"] = issue_text
                    request.session["issue_hash"] = issue_hash
                    request.session["searching"] = True
                    request.session["current_example_index"] = -1  # -1 means show loading
                    request.session["generated_examples"] = None  # Will be generated during loading
                    request.session["generated_rules"] = None  # Rules generated after labeling
                    request.session["example_labels"] = {}  # Clear previous labels
                    request.session["loading_screen_shown"] = False  # Reset flag for new search
                    request.session["in_workflow"] = True  # Mark that we're in a workflow
                    request.session.modified = True
                    print(f"DEBUG: New issue submitted: '{issue_text[:100]}...' (hash: {issue_hash})")
                    print(f"DEBUG: Cleared all cached data - will generate fresh examples from LLM")
                    # Redirect to show loading screen, examples will be generated in GET request
                    return redirect("home")
        
        # Handle marking an example as MATCH or NO_MATCH
        elif "mark_example" in request.POST:
            example_index = int(request.POST.get("example_index"))
            label = request.POST.get("label")  # MATCH or NO_MATCH
            
            # Store the label
            example_labels[str(example_index)] = label
            request.session["example_labels"] = example_labels
            request.session["in_workflow"] = True  # Keep workflow flag
            
            # Move to next example
            if example_index < total_examples - 1:
                request.session["current_example_index"] = example_index + 1
                return redirect("home")
            else:
                # All examples marked, generate rules from labeled examples
                # Build labeled examples with user's labels
                if deepsearch_issue and deepsearch_issue.get("examples"):
                    labeled_examples_list = []
                    for i, ex in enumerate(deepsearch_issue["examples"]):
                        label = example_labels.get(str(i), ex.get("user_label", "MATCH"))
                        labeled_examples_list.append({
                            "user": ex.get("user", ""),
                            "assistant": ex.get("assistant", ""),
                            "user_label": label,
                        })
                    
                    # Don't generate rules yet - will be generated during loading screen
                    # Show loading screen for rules generation
                    request.session["generating_rules"] = True
                    request.session["current_example_index"] = -3  # -3 means show generating rules loading
                    request.session["generated_rules"] = None  # Will be generated during loading
                    request.session["pending_labeled_examples"] = labeled_examples_list  # Store for generation
                    request.session["rules_loading_screen_shown"] = False  # Reset flag for new rules generation
                    request.session["in_workflow"] = True  # Keep workflow flag
                    return redirect("home")
        
        # Handle deploying a rule
        elif "deploy_rule" in request.POST:
            rule_id = request.POST.get("deploy_rule")
            # Mark rule as deployed in session
            if "deployed_rules" not in request.session:
                request.session["deployed_rules"] = []
            if rule_id not in request.session["deployed_rules"]:
                request.session["deployed_rules"].append(rule_id)
            request.session["in_workflow"] = True  # Keep workflow flag during deployment
            request.session.modified = True
            
            # Check if all rules are deployed
            deployed_rules = request.session.get("deployed_rules", [])
            rejected_rules = request.session.get("rejected_rules", [])
            # Get all suggested rules (not filtered) to check total count
            all_suggested_rules = request.session.get("generated_rules", [])
            if not all_suggested_rules:
                all_suggested_rules = suggested_rules
            total_rules = len(all_suggested_rules)
            
            # If all rules are deployed or rejected, redirect to home with reset
            if total_rules > 0 and len(deployed_rules) + len(rejected_rules) >= total_rules:
                request.session["example_labels"] = {}
                request.session["current_example_index"] = -2
                request.session["deployed_rules"] = []
                request.session["user_issue"] = None
                request.session["searching"] = False
                return redirect("home")
            
            # In real app, this would save to database
            # Return to same page (JavaScript shows loading for 10 seconds)
            return redirect("home")
        
        # Handle navigating to next rule
        elif "next_rule" in request.POST:
            # Get rules from session
            generated_rules = request.session.get("generated_rules", [])
            rejected_rules = request.session.get("rejected_rules", [])
            # Filter out rejected rules
            display_rules = [r for r in generated_rules if r.get("id") not in rejected_rules]
            current_rule_index = request.session.get("current_rule_index", 0)
            if current_rule_index < len(display_rules) - 1:
                request.session["current_rule_index"] = current_rule_index + 1
                print(f"DEBUG: Moving to next rule - new index: {current_rule_index + 1} of {len(display_rules)}")
            else:
                print(f"DEBUG: Already at last rule - index: {current_rule_index} of {len(display_rules)}")
            request.session["in_workflow"] = True
            request.session.modified = True
            return redirect("home")
        
        # Handle navigating to previous rule
        elif "previous_rule" in request.POST:
            current_rule_index = request.session.get("current_rule_index", 0)
            if current_rule_index > 0:
                request.session["current_rule_index"] = current_rule_index - 1
                print(f"DEBUG: Moving to previous rule - new index: {current_rule_index - 1}")
            else:
                print(f"DEBUG: Already at first rule - index: {current_rule_index}")
            request.session["in_workflow"] = True
            request.session.modified = True
            return redirect("home")
        
        # Handle rejecting a rule
        elif "reject_rule" in request.POST:
            rule_id = request.POST.get("reject_rule")
            # Mark rule as rejected in session
            if "rejected_rules" not in request.session:
                request.session["rejected_rules"] = []
            if rule_id not in request.session["rejected_rules"]:
                request.session["rejected_rules"].append(rule_id)
            request.session["in_workflow"] = True  # Keep workflow flag during rejection
            request.session.modified = True
            
            # Check if all rules are rejected or deployed
            rejected_rules = request.session.get("rejected_rules", [])
            deployed_rules = request.session.get("deployed_rules", [])
            # Get all suggested rules (not filtered) to check total count
            all_suggested_rules = request.session.get("generated_rules", [])
            if not all_suggested_rules:
                all_suggested_rules = suggested_rules
            total_rules = len(all_suggested_rules)
            
            # If all rules are rejected or deployed, redirect to home
            if total_rules > 0 and len(rejected_rules) + len(deployed_rules) >= total_rules:
                request.session["example_labels"] = {}
                request.session["current_example_index"] = -2
                request.session["deployed_rules"] = []
                request.session["rejected_rules"] = []
                request.session["user_issue"] = None
                request.session["searching"] = False
                request.session["generating_rules"] = False
                request.session["generated_examples"] = None
                request.session["generated_rules"] = None
                request.session["in_workflow"] = False  # Clear workflow flag when done
                return redirect("home")
            
            return redirect("home")
        
        # Handle reset (start over)
        elif "reset" in request.POST or request.GET.get("reset") == "1":
            request.session["example_labels"] = {}
            request.session["current_example_index"] = -2
            request.session["deployed_rules"] = []
            request.session["rejected_rules"] = []
            request.session["user_issue"] = None
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["in_workflow"] = False  # Clear workflow flag
            return redirect("home")
    
    # Initialize step variable (only if not already set by session_was_cleared check)
    if not (session_was_cleared and request.method == "GET"):
        step = "issue_input"
        current_example = None
        
        # Determine current step - prioritize showing issue input if no issue is set
        # OR if we don't have a complete workflow
        # IMPORTANT: Check searching state FIRST before other conditions
        if is_searching and current_index == -1:
            # Handle loading state - show loading screen
            step = "searching"
            current_example = None
        print(f"DEBUG: Setting step to 'searching' - is_searching={is_searching}, current_index={current_index}, generated_examples={generated_examples is not None}")
        
        # Check if we've already shown the loading screen (via session flag)
        # If not, set the flag and show loading screen (generation will happen on next refresh)
        # If yes, generate examples now
        loading_screen_shown = request.session.get("loading_screen_shown", False)
        if not loading_screen_shown:
            # First time showing loading screen, set flag
            request.session["loading_screen_shown"] = True
            request.session.modified = True
        elif generated_examples is None and user_issue:
            # Loading screen already shown, now generate examples
            print(f"DEBUG: ===== CALLING LLM TO GENERATE EXAMPLES =====")
            print(f"DEBUG: Issue: '{user_issue}'")
            print(f"DEBUG: Issue hash: {current_issue_hash}")
            print(f"DEBUG: This is a fresh LLM call - no cached examples used")
            try:
                examples = generate_examples_from_issue(user_issue)
                print(f"DEBUG: ===== LLM GENERATED {len(examples)} EXAMPLES =====")
                if examples:
                    print(f"DEBUG: First example user message: '{examples[0].get('user', '')[:100]}...'")
                    print(f"DEBUG: First example assistant message: '{examples[0].get('assistant', '')[:100]}...'")
                request.session["generated_examples"] = examples
                request.session["searching"] = False
                request.session["current_example_index"] = 0  # Move to first example
                request.session["loading_screen_shown"] = False  # Reset flag
                request.session["in_workflow"] = True  # Keep workflow flag
                request.session.modified = True
                # Redirect to show first example
                return redirect("home")
            except Exception as e:
                print(f"ERROR: Failed to generate examples: {e}")
                import traceback
                traceback.print_exc()
                # On error, reset to issue input and show error message
                request.session["user_issue"] = None
                request.session["current_example_index"] = -2
                request.session["searching"] = False
                request.session["generated_examples"] = None
                request.session["loading_screen_shown"] = False
                request.session["error_message"] = f"Failed to generate examples. Please try again. Error: {str(e)}"
                request.session.modified = True
                return redirect("home")
        elif is_generating_rules and current_index == -3:
            # Handle rules generation loading state
            step = "generating_rules"
            current_example = None
            print(f"DEBUG: Setting step to 'generating_rules' - is_generating_rules={is_generating_rules}, current_index={current_index}")
            
            # Check if we've already shown the loading screen (via session flag)
            # If not, set the flag and show loading screen (generation will happen on next refresh)
            # If yes, generate rules now
            rules_loading_screen_shown = request.session.get("rules_loading_screen_shown", False)
            if not rules_loading_screen_shown:
                # First time showing loading screen, set flag
                request.session["rules_loading_screen_shown"] = True
                request.session.modified = True
            elif generated_rules is None and user_issue:
                # Loading screen already shown, now generate rules
                pending_labeled_examples = request.session.get("pending_labeled_examples")
                if pending_labeled_examples:
                    print(f"DEBUG: ===== CALLING LLM TO GENERATE RULES =====")
                    print(f"DEBUG: Issue: '{user_issue}'")
                    print(f"DEBUG: Labeled examples count: {len(pending_labeled_examples)}")
                    print(f"DEBUG: This is a fresh LLM call - no cached rules used")
                    try:
                        rules = generate_suggested_rules_from_examples(user_issue, pending_labeled_examples)
                        print(f"DEBUG: ===== LLM GENERATED {len(rules)} RULES =====")
                        if rules:
                            print(f"DEBUG: First rule: '{rules[0].get('description', '')[:100]}...'")
                        request.session["generated_rules"] = rules
                        request.session["generating_rules"] = False
                        request.session["current_example_index"] = -1  # Move to rules review
                        request.session["pending_labeled_examples"] = None  # Clear temporary data
                        request.session["rules_loading_screen_shown"] = False  # Reset flag
                        request.session["in_workflow"] = True  # Keep workflow flag
                        request.session.modified = True
                        # Redirect to show rules review
                        return redirect("home")
                    except Exception as e:
                        print(f"ERROR: Failed to generate rules: {e}")
                        import traceback
                        traceback.print_exc()
                        # On error, reset to issue input and show error message
                        request.session["user_issue"] = None
                        request.session["current_example_index"] = -2
                        request.session["generating_rules"] = False
                        request.session["generated_rules"] = None
                        request.session["pending_labeled_examples"] = None
                        request.session["rules_loading_screen_shown"] = False
                        request.session["error_message"] = f"Failed to generate rules. Please try again. Error: {str(e)}"
                        request.session.modified = True
                        return redirect("home")
        # PRIORITY: If we have examples and a valid index, show labeling step
        # This must come BEFORE the checks that might reset to issue_input
        elif current_index >= 0 and generated_examples and user_issue:
            # Show current example for labeling (this is the normal flow after loading)
            step = "labeling_examples"
            if deepsearch_issue and deepsearch_issue.get("examples") and current_index < len(deepsearch_issue["examples"]):
                current_example = deepsearch_issue["examples"][current_index]
            else:
                current_example = None
            print(f"DEBUG: Showing labeling step - current_index={current_index}, total_examples={total_examples}")
        elif not user_issue or current_index == -2:
            # Show issue input form (home page)
            step = "issue_input"
            current_example = None
        # If we have a user_issue but no generated_examples, reset to issue input
        elif user_issue and not generated_examples:
            # Incomplete workflow, reset to issue input
            step = "issue_input"
            current_example = None
            # Clear the incomplete session state
            request.session["user_issue"] = None
            request.session["current_example_index"] = -2
            request.session["searching"] = False
            request.session["generating_rules"] = False
            request.session["generated_examples"] = None
            request.session["generated_rules"] = None
            request.session["example_labels"] = {}
            request.session.modified = True
        elif current_index == -1 and not is_searching:
            # At -1 and not searching - this means we're ready for rules review
            # Only show rules review if we have examples, rules, AND user has finished labeling
            if (deepsearch_issue and 
                deepsearch_issue.get("examples") and 
                len(deepsearch_issue.get("examples", [])) > 0 and
                suggested_rules and 
                len(suggested_rules) > 0 and
                len(example_labels) >= total_examples):  # User has labeled all examples
                # Show rules review stage
                step = "rules_review"
                current_example = None
                # Initialize current_rule_index if not set
                if "current_rule_index" not in request.session:
                    request.session["current_rule_index"] = 0
                    request.session.modified = True
            elif user_issue and generated_examples:
                # We have examples but user hasn't labeled them all yet, show first example
                step = "labeling_examples"
                if total_examples > 0:
                    # Reset to first example if we haven't started labeling
                    if len(example_labels) == 0:
                        request.session["current_example_index"] = 0
                        current_index = 0
                        request.session.modified = True
                    current_example = deepsearch_issue["examples"][current_index] if current_index < total_examples else None
                else:
                    current_example = None
            else:
                # No examples, show issue input
                step = "issue_input"
                current_example = None
        elif current_index >= total_examples:
            # Finished labeling all examples, show rules review if we have rules
            if (deepsearch_issue and 
                deepsearch_issue.get("examples") and 
                len(deepsearch_issue.get("examples", [])) > 0 and
                suggested_rules and 
                len(suggested_rules) > 0):
                # Show rules review stage
                step = "rules_review"
                current_example = None
                # Initialize current_rule_index if not set
                if "current_rule_index" not in request.session:
                    request.session["current_rule_index"] = 0
                    request.session.modified = True
            else:
                # No valid workflow, show issue input
                step = "issue_input"
                current_example = None
                # Clear incomplete session completely
                request.session["user_issue"] = None
                request.session["current_example_index"] = -2
                request.session["searching"] = False
                request.session["generating_rules"] = False
                request.session["generated_examples"] = None
                request.session["generated_rules"] = None
            request.session["example_labels"] = {}
            request.session.modified = True
            # Skip the rest of the rules review logic
            deepsearch_issue = None
            suggested_rules = []
    else:
        # Show current example for labeling
        step = "labeling_examples"
        if deepsearch_issue and deepsearch_issue.get("examples") and current_index < len(deepsearch_issue["examples"]):
            current_example = deepsearch_issue["examples"][current_index]
        else:
            current_example = None
    
    # Only build labeled examples and audit rules if we're actually showing rules review
    if step == "rules_review":
        # Build examples from user labels (only if deepsearch_issue exists)
        labeled_examples = []
        if deepsearch_issue and deepsearch_issue.get("examples"):
            for i, ex in enumerate(deepsearch_issue["examples"]):
                label = example_labels.get(str(i), ex.get("user_label", "MATCH"))  # Use stored label or default
                combined_text = f"User: {ex['user']}\nAssistant: {ex['assistant']}"
                labeled_examples.append({
                    "text": combined_text,
                    "label": label,
                })
        
        # Audit all suggested rules (if not already audited)
        for rule in suggested_rules:
            if rule.get("status") != "audited":
                examples_for_audit = labeled_examples.copy()
                examples_for_audit.append({
                    "text": rule["example"],
                    "label": "MATCH",
                })
                
                try:
                    commander = CommanderAgent(rule["description"], examples_for_audit)
                    audit_result = commander.audit_rule()
                    rule["audit_result"] = audit_result
                    rule["audit_result_json"] = json.dumps(audit_result, cls=DjangoJSONEncoder, default=str)
                    rule["status"] = "audited"
                    # Mark if LLM rejected the rule (but still show it)
                    if audit_result.get("executive_summary", {}).get("overall_status") == "REJECTED":
                        rule["llm_rejected"] = True
                except Exception as e:
                    rule["audit_error"] = str(e)
                    rule["status"] = "error"
    
    # Mark deployed and user-rejected rules
    deployed_rules = request.session.get("deployed_rules", [])
    rejected_rules = request.session.get("rejected_rules", [])
    for rule in suggested_rules:
        if rule["id"] in deployed_rules:
            rule["deployed"] = True
        if rule["id"] in rejected_rules:
            rule["user_rejected"] = True  # Changed from "rejected" to distinguish from LLM rejection
    
    # Show all rules - don't filter out LLM-rejected rules, only filter out user-rejected rules
    # LLM-rejected rules should still be visible so user can see them and decide
    display_rules = [r for r in suggested_rules if not r.get("user_rejected", False)]
    
    # On rules_review step, show only the current rule (one at a time)
    current_rule_index = request.session.get("current_rule_index", 0)
    if step == "rules_review" and display_rules:
        # Ensure current_rule_index is within bounds
        if current_rule_index >= len(display_rules):
            current_rule_index = len(display_rules) - 1
            request.session["current_rule_index"] = current_rule_index
            request.session.modified = True
        if current_rule_index < 0:
            current_rule_index = 0
            request.session["current_rule_index"] = current_rule_index
            request.session.modified = True
        # Show only the current rule
        current_rule = display_rules[current_rule_index] if current_rule_index < len(display_rules) else None
        display_rules = [current_rule] if current_rule else []
    else:
        current_rule = None
    
    # On the issue_input step, never show the issue (user hasn't selected one yet)
    # On all other steps, show the issue if it exists
    display_user_issue = None if step == "issue_input" else user_issue
    
    context = {
        "common_issues": common_issues,
        "user_issue": display_user_issue,  # Only show issue when not on issue_input step
        "deepsearch_issue": deepsearch_issue,
        "suggested_rules": display_rules,  # Only show current rule (or all rules if not in rules_review)
        "current_example_index": current_index,
        "current_example": current_example,
        "total_examples": total_examples,
        "example_labels": example_labels,
        "step": step,
        "progress": (len(example_labels) / total_examples * 100) if total_examples > 0 else 0,
        "deployed_rules": deployed_rules,
        "is_searching": is_searching,
        "is_generating_rules": is_generating_rules,
        "current_rule_index": current_rule_index,
        "total_rules": len([r for r in suggested_rules if not r.get("user_rejected", False)]),
    }
    return render(request, "commander/home.html", context)

