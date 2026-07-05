{% extends 'base.html' %}
{% block title %}{{ title | e }}{% endblock %}
{% block content %}
<div class="mt-4">
  <h2>{{ title | e }}</h2>
  <p class="text-muted small">Last updated: {{ note.updated_at.strftime('%Y-%m-%d %H:%M') }}</p>
  <div class="card mb-4"><div class="card-body">{{ body | e | replace('\n', '<br>') | safe }}</div></div>
  {% if is_owner %}
  <a href="{{ url_for('notes.edit_note', note_id=note.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
  <a href="{{ url_for('notes.share_note', note_id=note.id) }}" class="btn btn-sm btn-outline-secondary">Share</a>
  <form method="POST" action="{{ url_for('notes.delete_note', note_id=note.id) }}" class="d-inline" onsubmit="return confirm('Delete this note?')">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button class="btn btn-sm btn-outline-danger">Delete</button>
  </form>
  {% endif %}
  <a href="{{ url_for('notes.list_notes') }}" class="btn btn-sm btn-link">Back</a>
</div>
{% endblock %}
