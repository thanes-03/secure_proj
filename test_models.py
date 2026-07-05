{% extends 'base.html' %}
{% block title %}Transactions{% endblock %}
{% block content %}
<div class="mt-4">
  <h2>Transaction Receipts</h2>

  <h4 class="mt-4">Sent</h4>
  {% if sent %}
  <table class="table table-sm align-middle">
    <thead><tr><th>File</th><th>Recipient</th><th>Time</th><th></th></tr></thead>
    <tbody>
    {% for tx, fname in sent %}
      <tr>
        <td>{{ fname | e }}</td>
        <td>{{ tx.receiver_email | e }}</td>
        <td>{{ tx.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
        <td><a class="btn btn-sm btn-outline-primary"
               href="{{ url_for('notes.download_transaction', tx_id=tx.id) }}">Download</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="text-muted">No sent transactions.</p>{% endif %}

  <h4 class="mt-4">Received</h4>
  {% if received %}
  <table class="table table-sm align-middle">
    <thead><tr><th>File</th><th>Sender</th><th>Time</th><th></th></tr></thead>
    <tbody>
    {% for tx, fname in received %}
      <tr>
        <td>{{ fname | e }}</td>
        <td>{{ tx.sender_email | e }}</td>
        <td>{{ tx.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
        <td><a class="btn btn-sm btn-outline-primary"
               href="{{ url_for('notes.download_transaction', tx_id=tx.id) }}">Download</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="text-muted">No received transactions.</p>{% endif %}

  <a href="{{ url_for('notes.list_notes') }}" class="btn btn-sm btn-link">Back to notes</a>
</div>
{% endblock %}
