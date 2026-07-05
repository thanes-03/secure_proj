{% extends 'base.html' %}
{% block title %}{{ action }} Note{% endblock %}
{% block content %}
<div class="row justify-content-center mt-4">
  <div class="col-md-8">
    <h2>{{ action }} Note</h2>
    <form method="POST">
      {{ form.hidden_tag() }}
      <div class="mb-3">
        {{ form.title.label(class="form-label") }}
        {{ form.title(class="form-control") }}
        {% for e in form.title.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
      </div>
      <div class="mb-3">
        {{ form.body.label(class="form-label") }}
        {{ form.body(class="form-control", rows=10) }}
        {% for e in form.body.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
      </div>
      {{ form.submit(class="btn btn-primary") }}
      <a href="{{ url_for('notes.list_notes') }}" class="btn btn-secondary ms-2">Cancel</a>
    </form>
  </div>
</div>
{% endblock %}
