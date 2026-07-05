{% extends 'base.html' %}
{% block title %}Share Note{% endblock %}
{% block content %}
<div class="row justify-content-center mt-4">
  <div class="col-md-6">
    <h2>Share Note</h2>
    <form method="POST">
      {{ form.hidden_tag() }}
      <div class="mb-3">
        {{ form.recipient_email.label(class="form-label") }}
        {{ form.recipient_email(class="form-control", placeholder="friend@graduate.utm.my") }}
        {% for e in form.recipient_email.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
      </div>
      <div class="mb-3">
        <label class="form-label">Permission</label>
        <select name="permission" class="form-select">
          <option value="read">Read only</option>
          <option value="write">Read &amp; Write</option>
        </select>
      </div>
      {{ form.submit(class="btn btn-success") }}
      <a href="{{ url_for('notes.view_note', note_id=note_id) }}" class="btn btn-secondary ms-2">Cancel</a>
    </form>
  </div>
</div>
{% endblock %}
