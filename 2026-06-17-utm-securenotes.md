{% extends 'base.html' %}
{% block title %}Verify Email{% endblock %}
{% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-md-4">
    <h2 class="mb-4">Verify Your Email</h2>
    <p>Enter the 6-digit code sent to your UTM email.</p>
    <form method="POST">
      {{ form.hidden_tag() }}
      <div class="mb-3">
        {{ form.token.label(class="form-label") }}
        {{ form.token(class="form-control", maxlength=6, autocomplete="one-time-code") }}
        {% for e in form.token.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
      </div>
      {{ form.submit(class="btn btn-success w-100") }}
    </form>
    <form method="POST" action="{{ url_for('auth.resend_otp') }}" class="mt-2">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <button class="btn btn-link p-0">Resend code</button>
    </form>
  </div>
</div>
{% endblock %}
