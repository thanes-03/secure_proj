<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}UTM SecureNotes{% endblock %} — UTM SecureNotes</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('notes.list_notes') if session.get('user_id') else url_for('auth.login') }}">
      🔒 UTM SecureNotes
    </a>
    <div class="ms-auto d-flex gap-2">
      {% if session.get('user_id') %}
        <a href="{{ url_for('notes.list_transactions') }}" class="btn btn-sm btn-outline-light">Transactions</a>
        {% if session.get('is_admin') %}
        <a href="{{ url_for('admin.users') }}" class="btn btn-sm btn-outline-light">Admin</a>
        {% endif %}
        <form method="POST" action="{{ url_for('auth.logout') }}" class="d-inline">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <button class="btn btn-sm btn-outline-danger">Logout</button>
        </form>
      {% else %}
        <a href="{{ url_for('auth.login') }}" class="btn btn-sm btn-outline-light">Login</a>
        <a href="{{ url_for('auth.register') }}" class="btn btn-sm btn-light">Register</a>
      {% endif %}
    </div>
  </div>
</nav>
<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
    <div class="alert alert-{{ category }} mt-3" role="alert">{{ message | e }}</div>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
