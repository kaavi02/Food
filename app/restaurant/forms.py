from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange
from flask_wtf.file import FileField, FileAllowed

class RestaurantForm(FlaskForm):
    name = StringField('Restaurant Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    address = StringField('Address', validators=[DataRequired(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Length(max=120)])
    cuisine_type = StringField('Cuisine Type', validators=[Length(max=100)])
    delivery_fee = FloatField('Delivery Fee', validators=[NumberRange(min=0)])
    minimum_order = FloatField('Minimum Order Amount', validators=[NumberRange(min=0)])
    image = FileField('Restaurant Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'])])
    is_active = BooleanField('Active')
    submit = SubmitField('Save Restaurant')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    display_order = IntegerField('Display Order', default=0)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')

class FoodItemForm(FlaskForm):
    name = StringField('Food Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    image = FileField('Food Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'])])
    preparation_time = IntegerField('Preparation Time (mins)', validators=[NumberRange(min=0)])
    is_vegetarian = BooleanField('Vegetarian')
    is_vegan = BooleanField('Vegan')
    is_available = BooleanField('Available', default=True)
    submit = SubmitField('Save Food Item')
