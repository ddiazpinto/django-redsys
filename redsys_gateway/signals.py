from django.dispatch import Signal


pre_transaction = Signal(providing_args=["request", "form"])

post_transaction = Signal(providing_args=["response"])

transaction_accepted = Signal(providing_args=["response"])

transaction_rejected = Signal(providing_args=["response"])
