import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from services.library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)
from database import (get_all_books, get_book_by_isbn, get_db_connection)
from datetime import datetime, timedelta

# R1

def test_add_book_valid_input():
    success, message = add_book_to_catalog("Test Book 1", "Author A", "1000000000001", 5)
    assert success is True
    assert "successfully added" in message.lower()

def test_add_book_invalid_isbn():
    success, message = add_book_to_catalog("Test Book 2", "Author B", "12345", 5)
    assert success is False
    assert "exactly 13 digits" in message.lower()

def test_add_book_negative_copies():
    success, message = add_book_to_catalog("Test Book 3", "Author C", "1000000000003", -5)
    assert success is False
    assert "positive" in message.lower()

def test_add_book_duplicate_isbn():
    add_book_to_catalog("Book D", "Author D", "1000000000004", 5)
    success, message = add_book_to_catalog("Book E", "Author D", "1000000000004", 5)
    assert success is False
    assert "already exists" in message.lower()

# R2

def test_get_all_books_initially_empty():
    books = get_all_books()
    assert isinstance(books, list)
    assert len(books) == 0

def test_get_books_after_adding():
    add_book_to_catalog("Add Book 1", "Author 1", "1000000000007", 7)
    add_book_to_catalog("Add Book 2", "Author 2", "1000000000008", 7)
    books = get_all_books()
    assert any(book["title"] == "Add Book 1" for book in books)
    assert any(book["isbn"] == "1000000000008" for book in books)
    assert all("available_copies" in b for b in books)

def test_get_books_valid_isbn():
    add_book_to_catalog("Add Book 3", "Author 3", "1000000000009", 7)
    book = get_book_by_isbn("1000000000009")
    assert book is not None
    assert book["title"] == "Add Book 3"
    assert book["total_copies"] == 7

def test_get_books_invalid_isbn():
    book = get_book_by_isbn("9999999999999")
    assert book is None

# R3

def test_borrow_book_valid():
    add_book_to_catalog("Book Borrow 1", "Author E", "1000000000005", 5)
    success, message = borrow_book_by_patron("123456", 1)
    assert success is True
    assert "successfully borrowed" in message.lower()

def test_borrow_book_zero_copies():
    add_book_to_catalog("Book Borrow 2", "Author F", "1000000000006", 1)
    borrow_book_by_patron("123456", 2)
    success, message = borrow_book_by_patron("123456", 2)
    assert success is False
    assert "not available" in message.lower()

def test_borrow_patron_limit():
    for i in range(1, 6):
        add_book_to_catalog(f"Book{i}", "Author G", str(i).zfill(13), 5)
        borrow_book_by_patron("654321", i)
    add_book_to_catalog("Book Extra", "Author H", "1012".zfill(13), 5)
    success, message = borrow_book_by_patron("654321", 6)
    assert success is False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_nonexistent_book():
    patron_id = "888888"
    nonexistent_book_id = 9999

    success, message = borrow_book_by_patron(patron_id, nonexistent_book_id)
    assert success is False
    assert "not found" in message.lower()

# R4

def test_return_book_valid():
    success, message = return_book_by_patron("123456", 1)
    assert success is True
    assert "returned successfully" in message.lower()

def test_return_book_not_borrowed():
    success, message = return_book_by_patron("123456", 99)
    assert success is False
    assert "not borrowed" in message.lower()

def test_return_book_already_returned():
    success, message = return_book_by_patron("123456", 1)
    assert success is False
    assert "not borrowed" in message.lower()

def test_return_wrong_patron():
    borrow_book_by_patron("222222", 5)

    success, message = return_book_by_patron("123456", 5)
    assert success is False
    assert "not borrowed" in message.lower()

def test_return_nonexistent_book():
    success, message = return_book_by_patron("123456", 9999)
    assert success is False
    assert "book not found" in message.lower()

# R5

def overdue_scenario(isbn, patron_id, days_overdue):

    add_book_to_catalog(f"Overdue Book {isbn}", "Test Author", isbn, 5)
    book = get_book_by_isbn(isbn)
    borrow_book_by_patron(patron_id, book['id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    borrow_date = datetime.now() - timedelta(days=14 + days_overdue)
    due_date = datetime.now() - timedelta(days=days_overdue)
    cursor.execute("""
        UPDATE borrow_records 
        SET borrow_date = ?, due_date = ?
        WHERE patron_id = ? AND book_id = ? AND return_date IS NULL
    """, (borrow_date.isoformat(), due_date.isoformat(), patron_id, book['id']))
    conn.commit()
    conn.close()
    
    return book['id']

def test_late_fee_on_time():
    result = calculate_late_fee_for_book("123457", 2)
    fee = result['fee_amount']
    days = result['days_overdue']
    assert fee == 0
    assert days == 0

def test_late_fee_small_overdue():
    b_id = overdue_scenario("1000000000010", "123458", days_overdue=3)
    result = calculate_late_fee_for_book("123458", b_id)
    fee = result['fee_amount']
    days = result['days_overdue']
    assert fee <= 0.5 * 7
    assert days <= 7

def test_late_fee_big_overdue():
    b_id = overdue_scenario("1000000000011", "123459", days_overdue=10)
    result = calculate_late_fee_for_book("123459", b_id)
    fee = result['fee_amount']
    days = result['days_overdue']
    assert fee <= (1 * 7) + (0.5 * 7) and fee > 0.5 * 7
    assert days >= 7 and days > 0

def test_late_fee_max_limit():
    b_id = overdue_scenario("1000000000010", "123450", days_overdue=19)
    result = calculate_late_fee_for_book("123450", b_id)
    fee = result['fee_amount']
    days = result['days_overdue']
    assert fee == 15
    assert days == 19

def test_no_due_date():
    result = calculate_late_fee_for_book("123452", 12)
    fee = result['fee_amount']
    days = result['days_overdue']
    assert fee == 0.0
    assert days == 0.0

# R6

def test_search_title():
    search_results = search_books_in_catalog("Some Title", "title")
    assert isinstance(search_results, list)

def test_search_author():
    search_results = search_books_in_catalog("Author X", "author")
    assert isinstance(search_results, list)

def test_search_partial_title():
    search_results = search_books_in_catalog("Half", "title")
    assert isinstance(search_results, list)

def test_search_isbn_exact():
    search_results = search_books_in_catalog("4000000000001", "isbn")
    assert len(search_results) <= 1

def test_invalid_search_type():
    results = search_books_in_catalog("example", "invalid_type")
    assert results == []

# R7

def test_patron_status():
    status = get_patron_status_report("123456")
    assert isinstance(status, dict)

def test_patron_status_empty():
    status = get_patron_status_report("000000")
    assert isinstance(status, dict)
    assert len(status.get("borrowed_books", [])) == 0

def test_patron_status_some_books():
    status = get_patron_status_report("123456")
    assert isinstance(status, dict)
    assert "borrowed_books" in status

def test_patron_status_num_borrowed_books():
    status = get_patron_status_report("123456")
    
    assert isinstance(status, dict)
    assert "number_borrowed_books" in status
    assert isinstance(status["number_borrowed_books"], int)
    assert status["number_borrowed_books"] >= 0

def test_invalid_patron_id():
    status = get_patron_status_report("123abc")
    assert isinstance(status, dict)
    assert status == {}