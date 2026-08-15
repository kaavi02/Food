# Food Delivery Web Application

A full-stack food delivery platform built with Flask, Bootstrap 5, and MySQL.

## Features

*   **Role-Based Access Control:** Secure login/registration for Customers, Restaurant Owners, Delivery Partners, and Admins.
*   **Customer Experience:** Browse restaurants, view menus, search for food, add to cart, and checkout.
*   **Restaurant Dashboard:** Add, edit, and manage food categories and menu items. View incoming orders and analytics.
*   **Delivery Partner Dashboard:** Accept available orders, track active deliveries, and mark orders as delivered.
*   **Admin Panel:** Overview of platform statistics, manage users, and approve/deactivate restaurants.
*   **Online Payments:** Seamless integration with Razorpay (Test mode) for online transactions. Cash on Delivery (COD) is also supported.
*   **Order Tracking:** Customers can view their order history and current status.

## Tech Stack

*   **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate, Flask-Bcrypt, Flask-WTF
*   **Database:** MySQL (Aiven)
*   **Frontend:** HTML5, Jinja2 Templates, Bootstrap 5 (CDN), Custom CSS
*   **Payment Gateway:** Razorpay Python SDK

## Setup Instructions

1.  **Clone the Repository (or navigate to the project folder):**
    ```bash
    cd Kavya
    ```

2.  **Set up the Virtual Environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # On Windows
    # source venv/bin/activate  # On macOS/Linux
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Copy `.env.example` to `.env`.
    *   Update the `.env` file with your MySQL database URI and Razorpay API keys.

5.  **Initialize the Database:**
    *   Make sure your MySQL database server is running.
    *   Run migrations:
        ```bash
        flask db upgrade
        ```

6.  **Seed the Database (Optional but recommended for testing):**
    *   This will create demo accounts for each role and add sample restaurants.
    ```bash
    python scripts/seed.py
    ```
    *   *Demo Credentials:*
        *   Admin: `admin@food.com` / `password`
        *   Restaurant Owner: `spice@food.com` / `password`
        *   Delivery Partner: `delivery@food.com` / `password`
        *   Customer: `customer@food.com` / `password`

7.  **Run the Application:**
    ```bash
    python run.py
    # or
    flask run
    ```
    The app will be available at `http://127.0.0.1:5000`.

## Architecture Details

*   **Application Factory Pattern:** The app uses `create_app()` inside `app/__init__.py` to initialize extensions and blueprints, making it scalable and easier to test.
*   **Blueprints:** Routes are modularized into `auth`, `customer`, `restaurant`, `delivery`, and `admin`.
*   **Models:** Relational structure defines `User`, `Address`, `Restaurant`, `FoodCategory`, `FoodItem`, `Cart`, `Order`, and `Payment`.

## Development Notes
- The application uses `run.py` to launch with the instance variable `application` to avoid namespace conflicts with the `app` module for `flask db` commands.
- Images uploaded by restaurants are saved to `app/static/uploads`.
