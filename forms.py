from wtforms import Form, StringField, TextAreaField, validators

class NoteForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=255)])
    content = TextAreaField('Content', [validators.Length(min=1)])
    category = StringField('Category', [validators.Length(min=1)])
