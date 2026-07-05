{% extends 'base.html' %}
{% block title %}My Notes{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mt-4 mb-3">
  <h2>My Notes</h2>
  <a href="{{ url_for('notes.create_note') }}" class="btn btn-primary">+ New Note</a>
</div>
{% if owned %}
<h5>Owned</h5>
<ul class="list-group mb-4">
  {% for note, title in owned %}
  <li class="list-group-item d-flex justify-content-between">
    <a href="{{ url_for('notes.view_note', note_id=note.id) }}">{{ title | e }}</a>
    <small class="text-muted">{{ note.updated_at.strftime('%Y-%m-%d') }}</small>
  </li>
  {% endfor %}
</ul>
{% endif %}
{% if shared %}
<h5>Shared With Me</h5>
<ul class="list-group">
  {% for note, title in shared %}
  <li class="list-group-item">
    <a href="{{ url_for('notes.view_note', note_id=note.id) }}">{{ title | e }}</a>
  </li>
  {% endfor %}
</ul>
{% endif %}
{% if not owned and not shared %}
<p class="text-muted">No notes yet. <a href="{{ url_for('notes.create_note') }}">Create one.</a></p>
{% endif %}
{% endblock %}
