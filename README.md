<!DOCTYPE html>
<html>
<head>
</head>
<body>

<h1>mason-snd Application Documentation</h1>

<h2>Overview</h2>
<p>This document provides an overview of the key components of your Flask application, specifically focusing on the files <strong>routes.py</strong>, <strong>main.py</strong>, <strong>auth.py</strong>, <strong>forms.py</strong>, <strong>postres.py</strong>, and <strong>templates/dashboard.html</strong>.</p>

<h2>routes.py</h2>
<p>This file contains the route handlers that define the application's endpoints. It uses Flask Blueprints to segment different parts of your application into modules.</p>
<ul>
    <li><strong>Main Blueprint:</strong> Contains routes for index, dashboard, events, tournaments, and more.</li>
    <li><strong>Key Functions:</strong>
        <ul>
            <li><code>dashboard()</code>: Handles dashboard viewing and displays statistics based on user roles.</li>
            <li><code>get_team_stats()</code>: Retrieves team statistics such as total events and average scores.</li>
        </ul>
    </li>
</ul>

<h2>main.py</h2>
<p>This is the application entry point that initializes the Flask app, registers blueprints, and sets up the database. It also handles running the app in debug mode.</p>
<p>Key setup steps include database creation and blueprint registration.</p>

<h2>auth.py</h2>
<p>This file manages authentication routes and user management, such as login, logout, and account creation.</p>
<ul>
    <li><strong>Login:</strong> Verifies user credentials and initiates a session.</li>
    <li><strong>Signup:</strong> Registers a new user after validating inputs.</li>
    <li><strong>Account Management:</strong> Allows users to update their account details.</li>
</ul>

<h2>forms.py</h2>
<p>Defines WTForms used in the application for handling form data validation and rendering.</p>
<ul>
    <li><strong>LoginForm:</strong> Manages the login form fields and validations.</li>
    <li><strong>SignupForm:</strong> Manages user registration, including email and password validation.</li>
</ul>

<h2>postres.py</h2>
<p>This script handles the migration of a PostgreSQL database to SQLite, facilitating data transfer between different database environments.</p>
<ul>
    <li>Fetches data from PostgreSQL databases and transfers it to a local SQLite database.</li>
</ul>

<h2>templates/dashboard.html</h2>
<p>Defines the layout and data presentation for the dashboard view of the application.</p>
<ul>
    <li><strong>Role-based Display:</strong> Shows different data and metrics based on the user's role within the organization.</li>
    <li><strong>Tables:</strong> Displays user trends, team statistics, and allows interaction through forms.</li>
</ul>

</body>
</html>
