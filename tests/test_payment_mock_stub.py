import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment, add_book_to_catalog, borrow_book_by_patron
from services.payment_service import PaymentGateway

#Pay Late Fees Tests

def test_pay_late_fees_success(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book",
                 return_value={"fee_amount": 10.0, "days_overdue": 3},)
    mocker.patch("services.library_service.get_book_by_id",
        return_value={"title": "Book A"},
    )

    mockGateway = Mock(spec=PaymentGateway)
    mockGateway.process_payment.return_value = (True, "txn_001", "Success")

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is True
    assert transact == "txn_001"
    assert "Payment successful" in msg
    mockGateway.process_payment.assert_called_once_with(
        patron_id = "123456", amount=10.0, description="Late fees for 'Book A'")
    
def test_pay_late_fees_declined_by_gateway(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 15.0, "days_overdue": 5},
    )
    mocker.patch("services.library_service.get_book_by_id",
        return_value={"title": "Book B"},
    )

    mockGateway = Mock(spec=PaymentGateway)
    mockGateway.process_payment.return_value = (False, "", "Payment Declined")

    success, msg, transact = pay_late_fees("123456", 99, mockGateway)

    assert success is False
    assert transact is None
    assert "Payment failed" in msg
    mockGateway.process_payment.assert_called_once()

def test_pay_late_fees_invalid_patron_id(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.0},
    )
    mocker.patch("services.library_service.get_book_by_id", 
        return_value={"title": "Book C"})

    mockGateway = Mock(spec=PaymentGateway)

    success, msg, transact = pay_late_fees("A23456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "Invalid patron ID" in msg
    mockGateway.process_payment.assert_not_called()

def test_pay_late_fees_zero_fee(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0.0},
    )
    mocker.patch("services.library_service.get_book_by_id", 
        return_value={"title": "Book D"})

    mockGateway = Mock(spec=PaymentGateway)

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "No late fees" in msg
    mockGateway.process_payment.assert_not_called()

def test_pay_late_fees_network_error(mocker):
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 8.0, "days_overdue": 2},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"title": "Book E"},
    )

    mockGateway = Mock(spec=PaymentGateway)
    mockGateway.process_payment.side_effect = Exception("Network timeout")

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "Payment processing error" in msg
    mockGateway.process_payment.assert_called_once()

#Refund Late Fee Tests

def test_refund_late_fee_success(mocker):
    mockGateway = mocker.Mock(spec=PaymentGateway)
    mockGateway.refund_payment.return_value = (True, "Refund processed")

    success, msg = refund_late_fee_payment("txn_123", 5.0, mockGateway)

    assert success is True
    assert "Refund processed" in msg
    mockGateway.refund_payment.assert_called_once_with("txn_123", 5.0)

def test_refund_invalid_transaction_id():
    transact = "invalid_txn_001"
    mockGateway = Mock(spec=PaymentGateway)

    success, msg = refund_late_fee_payment(transact, 5.0, mockGateway)

    assert success is False
    assert "Invalid transaction ID" in msg
    mockGateway.refund_payment.assert_not_called()

def test_refund_invalid_amounts(mocker):
    mockGateway = mocker.Mock(spec=PaymentGateway)

    success, msg = refund_late_fee_payment("txn_123", -2, mockGateway)
    assert success is False
    assert "greater than 0" in msg

    success, msg = refund_late_fee_payment("txn_123", 0, mockGateway)
    assert success is False
    assert "greater than 0" in msg

    success, msg = refund_late_fee_payment("txn_123", 21, mockGateway)
    assert success is False
    assert "exceeds maximum" in msg

#Additional Tests to Increase Coverage

def test_add_book_empty_title():
    success, msg = add_book_to_catalog("Book 15", "AuthorX", "1234567890123", 1)
    assert success is False
    assert "Title is required" in msg

def test_add_book_long_title():
    long_title = "A" * 201
    success, msg = add_book_to_catalog(long_title, "AuthorY", "1234567890124", 1)
    assert success is False
    assert "less than 200 characters" in msg

def test_add_book_empty_author():
    success, msg = add_book_to_catalog("Title12", "AuthorZ", "1234567890125", 1)
    assert success is False
    assert "Author is required" in msg

def test_add_book_long_author():
    long_author = "A" * 101
    success, msg = add_book_to_catalog("Title13", long_author, "1234567890126", 1)
    assert success is False
    assert "less than 100 characters" in msg

def test_pay_late_fees_no_fee_info(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value=None)
    mockGateway = Mock(spec=PaymentGateway)

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "Unable to calculate late fees" in msg

def test_pay_late_fees_fee_info_missing_amount(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"days_overdue": 2})
    mockGateway = Mock(spec=PaymentGateway)

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "Unable to calculate late fees" in msg

def test_pay_late_fees_book_not_found(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 5.0})
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    mockGateway = Mock(spec=PaymentGateway)

    success, msg, transact = pay_late_fees("123456", 1, mockGateway)

    assert success is False
    assert transact is None
    assert "Book not found" in msg

def test_pay_late_fees_auto_create_gateway(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.0})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Book X"})
    mocker.patch("services.library_service.PaymentGateway.process_payment",
        return_value=(True, "txn_789", "Payment Success"))

    success, msg, transact = pay_late_fees("123456", 1)

    assert success is True
    assert transact == "txn_999"
    assert "Payment successful" in msg

def test_refund_failed():
    mockGateway = Mock()
    mockGateway.refund_payment.return_value = (False, "Refund Failed")

    success, msg = refund_late_fee_payment("txn_002", 5.0, payment_gateway=mockGateway)

    assert success is False
    assert "Refund failed" in msg

def test_refund_raises_exception():
    mockGateway = Mock()
    mockGateway.refund_payment.side_effect = Exception("Network error")

    success, msg = refund_late_fee_payment("txn_003", 5.0, payment_gateway=mockGateway)

    assert success is False
    assert "Refund processing error" in msg
