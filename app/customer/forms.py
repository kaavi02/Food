from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, RadioField
from wtforms.validators import DataRequired, Length

class AddressForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    address_line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=255)])
    address_line2 = StringField('Address Line 2', validators=[Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state = StringField('State', validators=[DataRequired(), Length(max=100)])
    postal_code = StringField('Postal Code', validators=[DataRequired(), Length(max=20)])
    landmark = StringField('Landmark', validators=[Length(max=255)])
    address_type = SelectField('Address Type', choices=[('home', 'Home'), ('work', 'Work'), ('other', 'Other')])
    submit = SubmitField('Save Address')

class CheckoutForm(FlaskForm):
    address_id = RadioField('Select Delivery Address', coerce=int, validators=[DataRequired()])
    payment_method = RadioField('Payment Method', choices=[('razorpay', 'Pay Online (Razorpay)'), ('cod', 'Cash on Delivery')], default='razorpay')
    special_instructions = TextAreaField('Special Instructions')
    submit = SubmitField('Place Order')
