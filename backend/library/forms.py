from django import forms


class OverdueEmailForm(forms.Form):
    language = forms.ChoiceField(
        label='메일 언어',
        choices=(('ko', '한국어'), ('de', 'Deutsch (독일어)')),
        initial='ko',
    )
