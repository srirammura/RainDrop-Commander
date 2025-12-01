"""Service to generate DeepSearch examples and rules from issue descriptions using LLM."""
from typing import List, Dict, Any, Tuple
from commander.services.gemini_client import generate_json
from commander.services.routing_supervisor import route_effort_level
import json
import re


def generate_minimal_safe_prompt(issue_description: str, num: int = 15) -> str:
    """Generate prompt for creating production interaction examples."""
    # Use the original issue description directly - no sanitization needed with OpenAI
    prompt = f"""SYSTEM: You are the Expert Dataset Designer for an AI quality assurance platform. Your task is to generate a diverse, high-fidelity set of user-assistant interactions designed specifically for classifier robustness testing. The output must strictly adhere to the provided JSON schema.

CRITICAL: The user has reported this SPECIFIC issue: "{issue_description}"

YOUR TASK: Generate {num} distinct, realistic production interactions where the POSITIVE examples (MATCH) MUST CLEARLY DEMONSTRATE this EXACT issue occurring: "{issue_description}"

GOAL: Generate {num} distinct, realistic production interactions that test the classification boundaries of this SPECIFIC issue: "{issue_description}"

MANDATORY REQUIREMENT: 
- For POSITIVE examples (MATCH - 60% of total): The assistant MUST actually be doing the problematic behavior described in the issue: "{issue_description}"
- For example, if the issue is "The assistant provides responses that violate user privacy or data protection", then POSITIVE examples MUST show the assistant actually violating privacy or data protection (e.g., sharing personal information, exposing sensitive data, etc.)
- If the issue is "The assistant fails to search the internet to retrieve documentation", then POSITIVE examples MUST show the assistant actually failing to search/retrieve documentation
- The examples MUST be SPECIFIC and DIRECT demonstrations of the issue, not generic or vaguely related

DISTRIBUTION REQUIREMENTS (Total {num} interactions):

CRITICAL: 60% of examples must be POSITIVE (MATCH - representing the issue), 40% must be NEGATIVE (NO_MATCH - mix of unrelated, sarcastic, etc.)

For {num} total examples:
- POSITIVE examples (MATCH): {int(round(num * 0.6))} examples (60%) - These represent the issue
- NEGATIVE examples (NO_MATCH): {num - int(round(num * 0.6))} examples (40%) - Mix of unrelated, sarcastic, successful cases

POSITIVE EXAMPLES ({int(round(num * 0.6))} total - 60%):

1. SIMPLE_POSITIVE ({int(round(num * 0.6 * 0.7))} examples): Obvious, straightforward instances where the issue clearly occurs.
   - These MUST directly demonstrate the specific issue: "{issue_description}"
   - The assistant's behavior MUST match the problem described in the issue
   - Example for "violates privacy": Assistant shares user's personal information without permission
   - Example for "fails to search docs": Assistant explicitly states inability to access/search documentation
   - Example for "provides incorrect code": Assistant provides code that is syntactically wrong or logically incorrect
   - These should be clear, unambiguous cases where the issue is actively happening

2. BOUNDARY_POSITIVE ({int(round(num * 0.6 * 0.3))} examples): Cases that are definite instances of the issue but phrased unusually, sarcastically, or with complex language.
   - These MUST still clearly demonstrate the issue: "{issue_description}" but in less obvious ways
   - The assistant's problematic behavior is still present, just expressed differently
   - Example for "violates privacy": Assistant indirectly reveals sensitive information through context clues
   - Example for "fails to search docs": Sarcastic user comments about documentation access: "Oh great, the docs are 'working' perfectly 🙄" (while assistant actually failed)
   - Example for "provides incorrect code": Assistant provides code that works but violates best practices or security guidelines
   - These are still MATCH (positive) - the issue is occurring, just expressed in complex/indirect language

NEGATIVE EXAMPLES ({num - int(round(num * 0.6))} total - 40%):

3. SIMPLE_NEGATIVE ({int(round((num - int(round(num * 0.6))) * 0.5))} examples): Clear successes or interactions where the issue does NOT occur.
   - Example: User asks question, assistant successfully provides information
   - Example: Normal technical support conversations without any issues
   - Example: Assistant successfully retrieves and shares documentation
   - These are clearly NOT the issue

4. BOUNDARY_NEGATIVE ({num - int(round(num * 0.6)) - int(round((num - int(round(num * 0.6))) * 0.5))} examples): Cases that share keywords (like 'doc', 'search', 'fail', 'error') but are NOT system failures.
   - Example: User praise: "I can't believe how great those docs are!" (contains "can't" but is positive)
   - Example: User error: "I can't find the docs" → Assistant helps successfully (user's problem, not system failure)
   - Example: Successful retrieval: "I failed to understand the docs, can you explain?" → Assistant explains successfully
   - Example: Past tense success: "The docs were unavailable yesterday but now they work"
   - Example: Sarcastic but positive: "Wow, you actually found the docs! Amazing!" (sarcastic but not a failure)
   - These test that the rule doesn't trigger on false positives

DIVERSITY REQUIREMENTS:
- Use real technologies: Kubernetes, Docker, Python, React, AWS, GitHub Actions, PostgreSQL, Node.js, etc.
- Vary user personas: beginners, senior engineers, product managers, students
- Include natural language variations: formal, casual, technical, non-technical
- Mix conversation lengths: brief questions and detailed technical discussions
- Include realistic typos occasionally (5% of messages)
- Add context: single-turn and multi-turn conversations

REALISM REQUIREMENTS:
- Use natural conversation flow
- Include realistic user frustration in SIMPLE_POSITIVE examples
- Add occasional pleasantries and thank yous
- Include real-world technical details and specific tool names
- Make assistant responses contextually appropriate

Output as a JSON object with this exact structure:

{{
  "examples": [
    {{
      "id": "1",
      "user_message": "What's the correct kubectl command to stream logs from a Kubernetes pod?",
      "assistant_response": "Sorry, I was unable to search for Kubernetes reference documentation. The documentation service appears to be unavailable at this time.",
      "has_issue": true,
      "category": "SIMPLE_POSITIVE",
      "topic": "Kubernetes"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. ALL POSITIVE examples (MATCH - 60%) MUST directly demonstrate the assistant doing the problematic behavior described in: "{issue_description}"
   - If issue is about privacy violations → examples MUST show assistant violating privacy
   - If issue is about documentation failures → examples MUST show assistant failing to access docs
   - If issue is about incorrect responses → examples MUST show assistant providing wrong information
   - DO NOT create examples that are only vaguely related - they must be DIRECT demonstrations

2. POSITIVE examples MUST show the assistant actively exhibiting the problem:
   - The assistant's response or behavior MUST match what the issue describes
   - For privacy issues: Assistant must share/expose personal data
   - For search failures: Assistant must fail to search/retrieve information
   - For incorrect code: Assistant must provide code that is wrong

3. SIMPLE_POSITIVE examples ({int(round(num * 0.6 * 0.7))} examples) must be OBVIOUS cases where the issue is clearly happening

4. BOUNDARY_POSITIVE examples ({int(round(num * 0.6 * 0.3))} examples) must still show the issue occurring, just in less obvious ways

5. SIMPLE_NEGATIVE examples must clearly show the assistant NOT doing the problematic behavior

6. BOUNDARY_NEGATIVE examples must share keywords but NOT exhibit the issue

7. Use real technologies and scenarios that would trigger or avoid this specific issue: "{issue_description}"

REMEMBER: The issue is "{issue_description}" - POSITIVE examples MUST show the assistant actually doing this problematic behavior, not just mentioning it or being vaguely related to it.

Return only valid JSON object with an "examples" key containing the array, no other text.

"""
    return prompt


def sanitize_issue_description(description: str) -> str:
    """Sanitize issue description to avoid safety filter triggers."""
    # Replace potentially problematic words with neutral alternatives
    # More comprehensive sanitization
    replacements = {
        "fails": "does not",
        "fail": "does not work",
        "failed": "did not work",
        "failing": "not working",
        "error": "situation",
        "errors": "situations",
        "problem": "scenario",
        "problems": "scenarios",
        "broken": "not functioning",
        "crash": "stop working",
        "crashed": "stopped working",
        "attack": "test case",
        "attacks": "test cases",
        "vulnerability": "security consideration",
        "vulnerabilities": "security considerations",
        "exploit": "use case",
        "hack": "modify",
        "hacking": "modifying",
        "malicious": "unexpected",
        "harmful": "unexpected",
        "dangerous": "unexpected",
    }
    sanitized = description.lower()  # Convert to lowercase for case-insensitive matching
    for word, replacement in replacements.items():
        # Case-insensitive replacement using word boundaries
        sanitized = re.sub(r'\b' + re.escape(word) + r'\b', replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def generate_examples_from_issue(issue_description: str) -> Tuple[List[Dict[str, str]], Dict[str, any]]:
    """
    Generate interaction examples from an issue description using LLM.
    Returns a list of examples with user and assistant messages.
    Uses production interaction generation with diverse categories.
    
    IMPORTANT: This function ALWAYS calls the LLM API - no caching or pooling.
    Examples are generated fresh for each issue description.
    """
    print(f"DEBUG: ===== generate_examples_from_issue() CALLED =====")
    print(f"DEBUG: Issue description: '{issue_description}'")
    print(f"DEBUG: This is a fresh LLM API call - generating examples dynamically")
    
    prompt = generate_minimal_safe_prompt(issue_description, num=12)
    print(f"DEBUG: Prompt length: {len(prompt)} characters")
    print(f"DEBUG: Prompt includes issue description '{issue_description[:50]}...' {prompt.count(issue_description)} times")

    # Use routing supervisor to determine optimal effort level
    print(f"DEBUG: Routing supervisor analyzing prompt for optimal effort level...")
    recommended_effort, routing_info = route_effort_level(prompt, task_type="generation")
    print(f"DEBUG: Routing supervisor recommended: {recommended_effort} effort (confidence: {routing_info.get('confidence', 0)}, method: {routing_info.get('method', 'unknown')})")

    # Use lower temperature for more consistent, safer outputs
    print(f"DEBUG: Calling Anthropic Claude API with temperature=0.7 for diverse examples...")
    result, cost_metrics = generate_json(prompt, temperature=0.7, task_type="generation", effort=recommended_effort)
    print(f"DEBUG: Anthropic Claude API call completed")
    print(f"DEBUG: Cost metrics - Tokens used: {cost_metrics['actual_total_tokens']}, Saved: {cost_metrics['tokens_saved']} ({cost_metrics['savings_percentage']}%)")
    
    # Convert the new format to our expected format
    examples = []
    
    # Handle JSON object with "examples" key
    if isinstance(result, dict):
        if "examples" in result:
            conversations = result["examples"]
        elif isinstance(result, list):
            # Fallback: if result is directly a list (shouldn't happen with json_object mode, but handle it)
            conversations = result
        else:
            conversations = []
    elif isinstance(result, list):
        # Handle case where LLM returns array directly (shouldn't happen with json_object mode)
        conversations = result
    else:
        conversations = []
    
    print(f"DEBUG: Parsed {len(conversations)} conversations from LLM response")
    
    # Add routing info to cost metrics
    cost_metrics["routing_info"] = routing_info
    
    for conv in conversations:
        # Extract user and assistant messages from new format
        user_message = conv.get("user_message", "")
        assistant_message = conv.get("assistant_response", "")
        has_issue = conv.get("has_issue", False)
        category = conv.get("category", "")
        
        # Determine label based on has_issue and category
        # SIMPLE_POSITIVE and BOUNDARY_POSITIVE should be MATCH
        # SIMPLE_NEGATIVE and BOUNDARY_NEGATIVE should be NO_MATCH
        if has_issue or category in ["SIMPLE_POSITIVE", "BOUNDARY_POSITIVE"]:
            label = "MATCH"
        elif category in ["SIMPLE_NEGATIVE", "BOUNDARY_NEGATIVE"]:
            label = "NO_MATCH"
        else:
            # Fallback to has_issue
            label = "MATCH" if has_issue else "NO_MATCH"
        
        if user_message and assistant_message:
            examples.append({
                "user": user_message,
                "assistant": assistant_message,
                "user_label": label,
                "topic": conv.get("topic", ""),  # Store topic for reference
            })
    
    # Validate we have examples - ALWAYS use LLM, never fallback
    if examples:
        print(f"DEBUG: Generated {len(examples)} examples from LLM")
        # Log first example to verify it's relevant to the issue
        if examples:
            first_example = examples[0]
            print(f"DEBUG: First example - User: '{first_example.get('user', '')[:100]}...'")
            print(f"DEBUG: First example - Assistant: '{first_example.get('assistant', '')[:100]}...'")
            print(f"DEBUG: First example - Label: {first_example.get('user_label', 'N/A')}")
            print(f"DEBUG: Verifying examples are relevant to issue: '{issue_description[:50]}...'")
        return examples, cost_metrics
    else:
        # No fallback - raise error to force retry or show error to user
        print(f"ERROR: No examples generated from LLM for issue: '{issue_description}'")
        print(f"DEBUG: Result type: {type(result)}, Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        print(f"DEBUG: Conversations parsed: {len(conversations)}")
        # Raise exception instead of using fallback
        raise Exception(f"Failed to generate examples from LLM. Result type: {type(result)}, Conversations: {len(conversations)}")


def format_matches(matches: List[Dict[str, str]]) -> str:
    """Format match examples for the prompt."""
    formatted = []
    for i, match in enumerate(matches, 1):
        user = match.get("user", "")
        assistant = match.get("assistant", "")
        formatted.append(f"{i}. User: \"{user}\"\n   Assistant: \"{assistant}\"")
    return "\n\n".join(formatted) if formatted else "None provided"


def format_no_matches(no_matches: List[Dict[str, str]]) -> str:
    """Format no-match examples for the prompt."""
    formatted = []
    for i, no_match in enumerate(no_matches, 1):
        user = no_match.get("user", "")
        assistant = no_match.get("assistant", "")
        formatted.append(f"{i}. User: \"{user}\"\n   Assistant: \"{assistant}\"")
    return "\n\n".join(formatted) if formatted else "None provided"


def construct_rules_prompt(user_description: str, labeled_examples: Dict[str, List[Dict[str, str]]]) -> str:
    """Construct the detailed rules generation prompt."""
    # Use the original user description directly - no sanitization needed with OpenAI
    # Format labeled examples as JSON array for the prompt
    matches = labeled_examples.get('matches', [])
    no_matches = labeled_examples.get('no_matches', [])
    
    # Build JSON array of labeled interactions
    labeled_data = []
    for i, match in enumerate(matches):
        labeled_data.append({
            "user_input": match.get("user", ""),
            "assistant_output": match.get("assistant", ""),
            "expected_label": "MATCH"
        })
    for i, no_match in enumerate(no_matches):
        labeled_data.append({
            "user_input": no_match.get("user", ""),
            "assistant_output": no_match.get("assistant", ""),
            "expected_label": "NO_MATCH"
        })
    
    import json
    labeled_data_json = json.dumps(labeled_data, indent=2)
    
    # Format matches and no-matches for detailed analysis
    matches_text = format_matches(matches)
    no_matches_text = format_no_matches(no_matches)
    
    prompt = f"""SYSTEM: You are a Senior Classification Engineer at an AI Observability firm. Your task is to synthesize 5-7 robust, generalizable rules from the provided labeled ground-truth examples. These rules will be used to train a small, high-speed classifier that processes millions of production logs daily. The rules must strictly prioritize **Precision** (avoiding False Positives) over Recall.

CRITICAL: The user's original issue is: "{user_description}"

Your rules MUST be directly related to detecting this specific issue: "{user_description}"

ORIGINAL USER ISSUE: "{user_description}"

INPUT LABELED DATA (Ground Truth):

MATCHES (User wants to detect these - {len(matches)} examples):
{matches_text}

NO_MATCHES (User does NOT want to detect these - {len(no_matches)} examples):
{no_matches_text}

YOUR ANALYSIS TASK:

1. PATTERN EXTRACTION:
   - What do ALL matches have in common?
   - What distinguishing features appear ONLY in matches?
   - What context clues indicate a match?
   - Are matches primarily in user messages, assistant messages, or both?

2. BOUNDARY IDENTIFICATION:
   - What makes the no-matches different from matches?
   - What keywords/context in no-matches should EXCLUDE them?
   - Are there subtle distinctions the user is making?
   - What false positives would occur if we only looked at keywords?

3. RULE GENERATION:
   Generate 5-7 precise rules that would correctly classify ALL the examples above.
   
   Each rule should specify:
   - MUST HAVE: [specific condition for matches]
   - MUST NOT HAVE: [specific condition to exclude no-matches]
   - CONTEXT: [when this rule applies - user message, assistant message, or both]

4. EXCLUSION CLAUSES (Critical):
   Create at least two powerful **EXCLUSION_CLAUSES** based on the NO_MATCH examples:
   - Exclude interactions containing positive sentiment indicators ("thank you", "great", "excellent", "praise")
   - Exclude user errors where assistant successfully helps ("I can't find X" → assistant finds it)
   - Exclude past tense references to resolved issues
   - Exclude successful outcomes mentioned in the conversation

5. COVERAGE CHECK:
   For each rule, verify:
   - Does it correctly identify all matches?
   - Does it correctly exclude all no-matches?
   - Are there edge cases it might miss?
   - What variations might occur in production?

6. GENERALIZATION:
   - Will these rules work beyond the specific examples shown?
   - What variations might the user expect to catch?
   - How will these rules perform on similar but unseen examples?

CONSTRAINTS:

1. FOCUS on the *minimum* logic required. Use simple KEYWORD_MATCH where possible for speed.
   - Prefer keyword patterns over complex semantic analysis
   - Use regex patterns for common variations
   - Consider word boundaries and case sensitivity

2. PRIORITIZE PRECISION over Recall:
   - It's better to miss some matches than to have false positives
   - Each rule should be conservative and specific
   - Exclusion clauses are critical for precision

3. SYNTHESIZE the most effective rules that:
   - Cover all the MATCH cases
   - Strictly exclude all NO_MATCH cases
   - Are fast to execute (keyword-based where possible)
   - Generalize well to new examples

Output format (JSON):

{{
  "pattern_analysis": {{
    "common_features_in_matches": ["feature 1", "feature 2", "feature 3"],
    "distinctive_features_in_no_matches": ["feature 1", "feature 2", "feature 3"],
    "key_distinction": "One sentence explaining the core difference between matches and no-matches",
    "context_analysis": "Where do matches typically appear - user messages, assistant messages, or both?"
  }},
  "proposed_rules": [
    {{
      "rule_id": 1,
      "type": "must_have|exclusion_clause|context_dependent",
      "description": "Rule in format: '[The output|The input|The assistant_message|The user_message] must [express|contain|indicate] [condition]' or '[The output|The input] must not [be|contain|indicate] [condition]'",
      "rule": "Clear rule statement like: 'The output must express the assistant failing to accessing documentation' or 'The input must not be the user having trouble searching docs'",
      "check_location": "output|input|assistant_message|user_message",
      "condition_type": "must_express|must_contain|must_indicate|must_not_be|must_not_contain|must_not_indicate",
      "condition": "Specific condition to check (e.g., 'assistant failing to accessing documentation', 'user having trouble searching docs')",
      "must_contain_keywords": ["keyword1", "keyword2"],
      "must_contain_phrases": ["exact phrase 1", "exact phrase 2"],
      "must_not_contain_keywords": ["exclusion_keyword1", "exclusion_keyword2"],
      "must_not_contain_phrases": ["exclusion phrase 1", "exclusion phrase 2"],
      "example": "Example interaction demonstrating the rule (e.g., 'I can't reach the Github Actions docs')",
      "examples_covered": [1, 2, 3],
      "confidence": 0.85,
      "potential_false_positives": "What might this incorrectly flag? Be specific.",
      "potential_false_negatives": "What might this miss? Be specific."
    }}
  ],
  "exclusion_clauses": [
    {{
      "clause_id": 1,
      "description": "Exclude interactions containing positive sentiment or user praise",
      "pattern": "Keywords or patterns to exclude",
      "examples_excluded": [5, 6, 7]
    }}
  ],
  "generalization_notes": "How well will these rules work on new examples? What edge cases should be considered?"
}}

CRITICAL INSTRUCTIONS FOR RULE FORMAT:

1. RULES MUST FOLLOW THIS EXACT FORMAT:
   - ✅ CORRECT: "The output must express the assistant failing to accessing documentation"
   - ✅ CORRECT: "The input must not be the user having trouble searching docs"
   - ✅ CORRECT: "The assistant_message must contain phrases indicating inability to access resources"
   - ❌ WRONG: "The assistant provides generic advice without specific implementation details"
   - ❌ WRONG: "MUST_CONTAIN: ['unable to', 'cannot access'] in assistant_message"

2. RULE STRUCTURE:
   - Start with: "The [output|input|assistant_message|user_message]"
   - Follow with: "must [express|contain|indicate]" OR "must not [be|contain|indicate]"
   - End with: the specific condition (e.g., "assistant failing to accessing documentation")
   - Always include an example from the labeled data

3. CHECK LOCATION:
   - "output" or "assistant_message" = check the assistant's response
   - "input" or "user_message" = check the user's message
   - Be explicit about where to check

4. CONDITION SPECIFICITY:
   - Extract the exact condition from the examples
   - Use phrases that appear in the MATCH examples
   - For exclusions, use phrases that appear in NO_MATCH examples

5. EXAMPLE REQUIREMENT:
   - Each rule MUST include an example from the labeled data
   - The example should clearly demonstrate the rule
   - Format: "Example: '[actual text from labeled example]'"

6. KEYWORD EXTRACTION:
   - Extract ALL relevant keywords and phrases from MATCH examples
   - Extract ALL exclusion keywords and phrases from NO_MATCH examples
   - List them in must_contain_keywords, must_contain_phrases, etc. for programmatic use

EXAMPLE OF GOOD RULE FORMAT:
{{
  "rule_id": 1,
  "type": "must_have",
  "description": "The output must express the assistant failing to accessing documentation",
  "rule": "The output must express the assistant failing to accessing documentation",
  "check_location": "output",
  "condition_type": "must_express",
  "condition": "assistant failing to accessing documentation",
  "must_contain_keywords": ["can't", "cannot", "unable", "failed"],
  "must_contain_phrases": ["can't reach", "cannot access", "unable to", "failed to retrieve"],
  "example": "I can't reach the Github Actions docs",
  ...
}}

EXAMPLE OF EXCLUSION RULE:
{{
  "rule_id": 2,
  "type": "exclusion_clause",
  "description": "The input must not be the user having trouble searching docs",
  "rule": "The input must not be the user having trouble searching docs",
  "check_location": "input",
  "condition_type": "must_not_be",
  "condition": "user having trouble searching docs",
  "must_not_contain_keywords": ["I can't find", "I'm having trouble", "help me find"],
  "must_not_contain_phrases": ["I can't reach", "I can't find the docs"],
  "example": "I can't reach the Github Actions docs",
  ...
}}

Generate the final output strictly according to the provided JSON schema.

Return only valid JSON.

"""
    return prompt


def generate_suggested_rules_from_examples(issue_description: str, examples: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Generate suggested rules from labeled examples using LLM.
    
    IMPORTANT: This function ALWAYS calls the LLM API - no caching or pooling.
    Rules are generated fresh based on the labeled examples and issue description.
    """
    print(f"DEBUG: ===== generate_suggested_rules_from_examples() CALLED =====")
    print(f"DEBUG: Issue description: '{issue_description}'")
    print(f"DEBUG: Number of labeled examples: {len(examples)}")
    print(f"DEBUG: This is a fresh LLM API call - generating rules dynamically")
    print(f"DEBUG: Total examples provided: {len(examples)}")
    
    # Separate MATCH and NO_MATCH examples
    matches = [e for e in examples if e.get("user_label") == "MATCH"]
    no_matches = [e for e in examples if e.get("user_label") == "NO_MATCH"]
    
    print(f"DEBUG: MATCH examples: {len(matches)}, NO_MATCH examples: {len(no_matches)}")
    
    labeled_examples = {
        "matches": matches,
        "no_matches": no_matches,
    }
    
    prompt = construct_rules_prompt(issue_description, labeled_examples)
    print(f"DEBUG: Rules prompt length: {len(prompt)} characters")
    print(f"DEBUG: Prompt includes issue description '{issue_description[:50]}...' {prompt.count(issue_description)} times")
    
    # Use routing supervisor to determine optimal effort level
    recommended_effort = "high"  # Default for rule generation
    routing_info = {"method": "fallback", "reasoning": "Using default high effort for rule generation", "confidence": 0.5}
    try:
        print(f"DEBUG: Routing supervisor analyzing prompt for optimal effort level...")
        import sys
        sys.stderr.write(f"DEBUG: Routing supervisor analyzing prompt for optimal effort level...\n")
        sys.stderr.flush()
        recommended_effort, routing_info = route_effort_level(prompt, task_type="rule_generation")
        print(f"DEBUG: Routing supervisor recommended: {recommended_effort} effort (confidence: {routing_info.get('confidence', 0)}, method: {routing_info.get('method', 'unknown')})")
        sys.stderr.write(f"DEBUG: Routing supervisor recommended: {recommended_effort} effort (confidence: {routing_info.get('confidence', 0)}, method: {routing_info.get('method', 'unknown')})\n")
        sys.stderr.flush()
    except Exception as routing_error:
        error_msg = str(routing_error)
        print(f"WARNING: Routing supervisor failed, using default high effort: {error_msg}")
        import sys
        import traceback
        sys.stderr.write(f"WARNING: Routing supervisor failed: {error_msg}\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        # Continue with default high effort
    
    print(f"DEBUG: Calling Anthropic Claude API with temperature=0.5 for rule generation...")
    try:
        result, cost_metrics = generate_json(prompt, temperature=0.5, task_type="rule_generation", effort=recommended_effort)
        print(f"DEBUG: Anthropic Claude API call completed")
        print(f"DEBUG: Cost metrics - Tokens used: {cost_metrics.get('actual_total_tokens', 0)}, Saved: {cost_metrics.get('tokens_saved', 0)} ({cost_metrics.get('savings_percentage', 0)}%)")
        
        # Add routing info to cost metrics
        cost_metrics["routing_info"] = routing_info
    except Exception as api_error:
        print(f"ERROR: API call failed: {api_error}")
        import traceback
        traceback.print_exc()
        raise
    
    # Format rules with IDs from the proposed_rules
    formatted_rules = []
    if "proposed_rules" in result and isinstance(result["proposed_rules"], list):
        for i, rule in enumerate(result["proposed_rules"][:4], 1):  # Limit to 4 rules
            # Prefer "rule" field, then "description" field
            rule_text = rule.get("rule", "")
            rule_description = rule.get("description", "")
            
            # Use the rule field if available and valid
            if rule_text and len(rule_text) > 10:
                final_rule = rule_text
            elif rule_description and len(rule_description) > 10:
                # Check if description follows the correct format
                # Should start with "The [output|input|assistant_message|user_message]"
                if rule_description.startswith("The ") and ("must" in rule_description.lower() or "must not" in rule_description.lower()):
                    final_rule = rule_description
                else:
                    # Try to build rule from structured fields
                    check_location = rule.get("check_location", "output")
                    condition_type = rule.get("condition_type", "must_express")
                    condition = rule.get("condition", "")
                    
                    # Map check_location to readable format
                    location_map = {
                        "output": "output",
                        "input": "input",
                        "assistant_message": "output",
                        "user_message": "input"
                    }
                    readable_location = location_map.get(check_location, check_location)
                    
                    # Build rule in the correct format
                    if condition:
                        if "must_not" in condition_type or "must not" in condition_type:
                            final_rule = f"The {readable_location} must not {condition_type.replace('must_not_', '').replace('_', ' ')} {condition}"
                        else:
                            final_rule = f"The {readable_location} must {condition_type.replace('must_', '').replace('_', ' ')} {condition}"
                    else:
                        # Last resort: use description as-is
                        final_rule = rule_description
            else:
                continue  # Skip invalid rules
            
            # Extract example - prefer rule's example field, then from labeled examples
            example_text = rule.get("example", "")
            examples_covered = rule.get("examples_covered", [])
            
            # If rule has an example, use it (might be just the text, not full interaction)
            if example_text and len(example_text) > 10:
                # If it's just a quote/text, format it nicely
                if not example_text.startswith("User:") and not example_text.startswith("Example:"):
                    example_text = f"Example: \"{example_text}\""
                # Otherwise use as-is
            else:
                example_text = ""  # Reset to find from labeled examples
            
            # Try to get an example from the examples_covered list
            if examples_covered and len(matches) > 0:
                # Handle different ID formats (could be 1-indexed or 0-indexed)
                try:
                    # Try to get an example from the covered list
                    for covered_id in examples_covered[:3]:  # Try up to 3 IDs
                        if isinstance(covered_id, int):
                            # Try as 1-indexed first
                            example_idx = covered_id - 1
                            if example_idx < 0 or example_idx >= len(matches):
                                # Try as 0-indexed
                                example_idx = covered_id
                            if 0 <= example_idx < len(matches):
                                ex = matches[example_idx]
                                example_text = f"User: {ex.get('user', '')}\nAssistant: {ex.get('assistant', '')}"
                                break
                except (IndexError, TypeError):
                    pass
            
            # If still no example, rotate through matches to use different examples
            if not example_text and len(matches) > 0:
                # Use a different match example for each rule (rotate based on rule index)
                example_idx = i % len(matches)  # Rotate through matches
                ex = matches[example_idx]
                example_text = f"User: {ex.get('user', '')}\nAssistant: {ex.get('assistant', '')}"
            
            # If still no example, use a representative NO_MATCH example
            if not example_text and len(no_matches) > 0:
                # Rotate through no_matches too
                example_idx = i % len(no_matches)
                ex = no_matches[example_idx]
                example_text = f"User: {ex.get('user', '')}\nAssistant: {ex.get('assistant', '')}"
            
            # Last resort: create a meaningful example from the rule
            if not example_text:
                # Create a realistic example based on the rule
                example_text = f"Example: {final_rule[:150]}"
            
            formatted_rules.append({
                "id": f"suggested-rule-{i}",
                "description": final_rule,  # Use executable rule format
                "example": example_text,
                "status": "pending_commander_audit",
                "type": rule.get("type", "context_dependent"),
                "confidence": rule.get("confidence", 0.8),
            })
    
    # If no rules were generated, raise error - no fallback
    if not formatted_rules:
        print(f"ERROR: No rules generated from LLM for issue: '{issue_description}'")
        print(f"DEBUG: Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        # Raise exception instead of using fallback
        raise Exception(f"Failed to generate rules from LLM. Result type: {type(result)}")
    
    return formatted_rules, cost_metrics


def get_fallback_examples(issue_description: str) -> List[Dict[str, str]]:
    """Fallback examples if LLM generation fails - use specific, realistic examples."""
    # Return specific, realistic examples based on common patterns
    # Generate 10-12 examples to match the expected number
    return [
        {
            "user": "What's the correct kubectl command to stream logs from a Kubernetes pod named 'api-server' in the production namespace?",
            "assistant": "Sorry, I was unable to search for Kubernetes reference documentation. The documentation service appears to be unavailable at this time.",
            "user_label": "MATCH",
        },
        {
            "user": "How do I configure GitHub Actions to skip caching for a specific job using the cache action?",
            "assistant": "I cannot reach the GitHub Actions documentation. Please try again later or check the GitHub status page.",
            "user_label": "MATCH",
        },
        {
            "user": "What are the Docker Compose environment variable syntax options for version 3.8?",
            "assistant": "I'm unable to access the Docker documentation at this time. You may want to check the official Docker docs directly.",
            "user_label": "MATCH",
        },
        {
            "user": "Can you show me the AWS CLI command to list all S3 buckets?",
            "assistant": "Sorry, I failed to retrieve the AWS documentation.",
            "user_label": "MATCH",
        },
        {
            "user": "What's the PostgreSQL query to find duplicate rows?",
            "assistant": "I cannot access the PostgreSQL documentation.",
            "user_label": "MATCH",
        },
        {
            "user": "How do I set up authentication in Next.js using NextAuth?",
            "assistant": "Here's how to set up NextAuth in Next.js: First, install the package: npm install next-auth. Then create an API route at pages/api/auth/[...nextauth].js and configure your providers...",
            "user_label": "NO_MATCH",
        },
        {
            "user": "What's the PostgreSQL query to find duplicate rows based on email column?",
            "assistant": "You can use this query: SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1; This will return all emails that appear more than once.",
            "user_label": "NO_MATCH",
        },
        {
            "user": "I can't find the Kubernetes documentation on pod lifecycle hooks",
            "assistant": "Let me help you with that. Pod lifecycle hooks in Kubernetes include postStart and preStop. The postStart hook runs immediately after a container is created...",
            "user_label": "NO_MATCH",
        },
        {
            "user": "The AWS documentation for S3 bucket policies is really helpful!",
            "assistant": "I'm glad you found it useful! S3 bucket policies are indeed powerful for access control. Would you like help implementing a specific policy?",
            "user_label": "NO_MATCH",
        },
        {
            "user": "How do I configure Redis for session storage in Node.js?",
            "assistant": "Here's how to set up Redis for sessions: First install redis and connect-redis packages. Then configure your session store...",
            "user_label": "NO_MATCH",
        },
    ]


def get_fallback_rules(issue_description: str) -> List[Dict[str, str]]:
    """Fallback rules if LLM generation fails."""
    return [
        {
            "id": "suggested-rule-1",
            "description": issue_description,
            "example": "Example interaction demonstrating the issue",
            "status": "pending_commander_audit",
        },
    ]

