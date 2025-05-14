not all([data.get(k) for k in ('name', 'date', 'time')]):
        return jsonify({"error": "Missing data"}), 400
    success = cancel_appointment(data['name'], dat