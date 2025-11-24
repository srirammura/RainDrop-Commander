from django import forms


class ExampleForm(forms.Form):
    """Form for a single example."""
    text = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            "class": "example-text",
            "placeholder": "Example text...",
        })
    )
    label = forms.ChoiceField(
        choices=[("MATCH", "MATCH"), ("NO_MATCH", "NO_MATCH")],
        widget=forms.Select(attrs={
            "class": "example-label",
        })
    )


class RuleAuditForm(forms.Form):
    """Form for rule audit input."""
    rule_description = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            "class": "rule-description",
            "placeholder": "e.g., Fails to reach documentation",
            "rows": 3,
        }),
        label="Rule Description"
    )

