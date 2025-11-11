import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment, add_book_to_catalog, borrow_book_by_patron, get_book_by_isbn, return_book_by_patron
from services.payment_service import PaymentGateway
from database import get_db_connection
from datetime import datetime, timedelta

#Resetting Database
@pytest.fixture(autouse=True)
def reset_db_before_test():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM borrow_records")
    cursor.execute("DELETE FROM books")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='books'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='borrow_records'")
    conn.commit()
    conn.close()
    yield

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
    success, msg = add_book_to_catalog("", "AuthorX", "1234567890123", 1)
    assert success is False
    assert "Title is required" in msg

def test_add_book_long_title():
    long_title = "A" * 201
    success, msg = add_book_to_catalog(long_title, "AuthorY", "1234567890124", 1)
    assert success is False
    assert "less than 200 characters" in msg

def test_add_book_empty_author():
    success, msg = add_book_to_catalog("Title12", "", "1234567890125", 1)
    assert success is False
    assert "Author is required" in msg

def test_add_book_long_author():
    long_author = "A" * 101
    success, msg = add_book_to_catalog("Title13", long_author, "1234567890126", 1)
    assert success is False
    assert "less than 100 characters" in msg

def test_borrow_invalid_patron_id():
    add_book_to_catalog("Test Book Invalid", "Author I", "1000000000012", 5)
    book = get_book_by_isbn("1000000000012")
    success, message = borrow_book_by_patron("A23B34", book['id'])
    assert success is False
    assert "invalid patron id" in message.lower()

def test_borrow_limit_exceeded():
    patron_id = "777777"
    for i in range(1, 7):
        isbn = str(200 + i).zfill(13)
        add_book_to_catalog(f"Limit Book {i}", "Author L", isbn, 5)
        book = get_book_by_isbn(isbn)
        borrow_book_by_patron(patron_id, book['id'])
    
    add_book_to_catalog("Extra Limit Book", "Author M", "3000000000001", 5)
    extra_book = get_book_by_isbn("3000000000001")
    success, message = borrow_book_by_patron(patron_id, extra_book['id'])
    assert success is False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_db_insert_failure(mocker):
    add_book_to_catalog("DB Fail Book", "Author N", "4000000000001", 5)
    book = get_book_by_isbn("4000000000001")
    
    mocker.patch("services.library_service.insert_borrow_record", return_value=False)
    
    success, message = borrow_book_by_patron("123456", book['id'])
    assert success is False
    assert "database error occurred" in message.lower()

def test_borrow_update_availability_failure(mocker):
    add_book_to_catalog("Avail Fail Book", "Author O", "5000000000001", 5)
    book = get_book_by_isbn("5000000000001")
    
    mocker.patch("services.library_service.update_book_availability", return_value=False)
    
    success, message = borrow_book_by_patron("123456", book['id'])
    assert success is False
    assert "database error occurred while updating book availability" in message.lower()

def test_return_invalid_patron_id():
    add_book_to_catalog("Return Book Invalid", "Author P", "6000000000001", 5)
    book = get_book_by_isbn("6000000000001")
    borrow_book_by_patron("123456", book['id'])

    success, message = return_book_by_patron("12AB34", book['id'])
    assert success is False
    assert "invalid patron id" in message.lower()

def test_return_record_update_failure(mocker):
    add_book_to_catalog("Record Fail Book", "Author Q", "6000000000002", 5)
    book = get_book_by_isbn("6000000000002")
    borrow_book_by_patron("123456", book['id'])

    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=False)

    success, message = return_book_by_patron("123456", book['id'])
    assert success is False
    assert "could not record return" in message.lower()

def test_return_update_availability_failure(mocker):
    add_book_to_catalog("Avail Fail Return", "Author R", "6000000000003", 5)
    book = get_book_by_isbn("6000000000003")
    borrow_book_by_patron("123456", book['id'])

    mocker.patch("services.library_service.update_book_availability", return_value=False)

    success, message = return_book_by_patron("123456", book['id'])
    assert success is False
    assert "could not update availability" in message.lower()

def test_return_book_with_late_fee():
    isbn = "6000000000004"
    add_book_to_catalog("Late Fee Book", "Author S", isbn, 5)
    book = get_book_by_isbn(isbn)
    borrow_book_by_patron("123456", book['id'])

    # Manually make it overdue
    conn = get_db_connection()
    cursor = conn.cursor()
    borrow_date = datetime.now() - timedelta(days=20)
    due_date = datetime.now() - timedelta(days=10)
    cursor.execute("""
        UPDATE borrow_records 
        SET borrow_date = ?, due_date = ?
        WHERE patron_id = ? AND book_id = ?
    """, (borrow_date.isoformat(), due_date.isoformat(), "123456", book['id']))
    conn.commit()
    conn.close()

    success, message = return_book_by_patron("123456", book['id'])
    assert success is True
    assert "late fee" in message.lower()


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
    assert transact == "txn_789"
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
