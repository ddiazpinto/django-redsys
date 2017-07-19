from django.dispatch import Signal


pre_transaction = Signal(providing_args=["request", "order_object", "transaction_request"])

post_transaction = Signal(providing_args=["request", "transaction_response"])

transaction_accepted = Signal(providing_args=["request", "transaction_response"])

transaction_rejected = Signal(providing_args=["request", "transaction_response"])

invalid_response = Signal(providing_args=["request", "form"])

suspicious_response = Signal(providing_args=["request", "form"])
