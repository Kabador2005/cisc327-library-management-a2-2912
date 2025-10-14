import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path BEFORE importing library_service
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)

"""
Comprehensive Test Suite for Library Management System
Tests for Requirements R1-R7
"""


class TestR1_AddBookToCatalog(unittest.TestCase):
    """Test cases for R1: Adding a book to the catalog"""
    
    @patch('library_service.get_book_by_isbn')
    @patch('library_service.insert_book')
    def test_add_valid_book(self, mock_insert, mock_get_isbn):
        """TC-R1-01: Add a book with all valid fields"""
        mock_get_isbn.return_value = None
        mock_insert.return_value = True
        
        success, message = add_book_to_catalog("Effective Java", "Joshua Bloch", "9780134685991", 5)
        
        self.assertTrue(success)
        self.assertIn("successfully added", message)
        mock_insert.assert_called_once_with("Effective Java", "Joshua Bloch", "9780134685991", 5, 5)
    
    @patch('library_service.get_book_by_isbn')
    def test_add_duplicate_isbn(self, mock_get_isbn):
        """TC-R1-02: Attempt to add a book with duplicate ISBN"""
        mock_get_isbn.return_value = {"id": 1, "isbn": "9780134685991"}
        
        success, message = add_book_to_catalog("Book Two", "Different Author", "9780134685991", 2)
        
        self.assertFalse(success)
        self.assertEqual(message, "A book with this ISBN already exists.")
    
    def test_add_book_invalid_isbn_length(self):
        """TC-R1-03: Add book with invalid ISBN length"""
        success, message = add_book_to_catalog("Test Book", "Author", "123", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "ISBN must be exactly 13 digits.")
    
    def test_add_book_empty_title(self):
        """TC-R1-04: Add book with empty title"""
        success, message = add_book_to_catalog("", "Author", "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Title is required.")
    
    def test_add_book_whitespace_title(self):
        """TC-R1-05: Add book with whitespace-only title"""
        success, message = add_book_to_catalog("   ", "Author", "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Title is required.")
    
    def test_add_book_title_too_long(self):
        """TC-R1-06: Add book with title exceeding 200 characters"""
        long_title = "A" * 201
        success, message = add_book_to_catalog(long_title, "Author", "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Title must be less than 200 characters.")
    
    def test_add_book_empty_author(self):
        """TC-R1-07: Add book with empty author"""
        success, message = add_book_to_catalog("Test Book", "", "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Author is required.")
    
    def test_add_book_author_too_long(self):
        """TC-R1-08: Add book with author exceeding 100 characters"""
        long_author = "B" * 101
        success, message = add_book_to_catalog("Test Book", long_author, "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Author must be less than 100 characters.")
    
    def test_add_book_negative_copies(self):
        """TC-R1-09: Add book with negative number of copies"""
        success, message = add_book_to_catalog("Test Book", "Author", "9780134685991", -1)
        
        self.assertFalse(success)
        self.assertEqual(message, "Total copies must be a positive integer.")
    
    def test_add_book_zero_copies(self):
        """TC-R1-10: Add book with zero copies"""
        success, message = add_book_to_catalog("Test Book", "Author", "9780134685991", 0)
        
        self.assertFalse(success)
        self.assertEqual(message, "Total copies must be a positive integer.")
    
    @patch('library_service.get_book_by_isbn')
    @patch('library_service.insert_book')
    def test_add_book_database_error(self, mock_insert, mock_get_isbn):
        """TC-R1-11: Handle database error during insertion"""
        mock_get_isbn.return_value = None
        mock_insert.return_value = False
        
        success, message = add_book_to_catalog("Test Book", "Author", "9780134685991", 5)
        
        self.assertFalse(success)
        self.assertEqual(message, "Database error occurred while adding the book.")


class TestR2_DisplayCatalog(unittest.TestCase):
    """Test cases for R2: Display the catalog (tested through web interface)"""
    
    def test_display_requirement_note(self):
        """TC-R2-01: Note that R2 is primarily tested through integration tests"""
        # R2 is handled by Flask routes and templates
        # The display logic uses get_all_books() from database module
        # Unit tests would focus on the database query function
        pass


class TestR3_BorrowingBooks(unittest.TestCase):
    """Test cases for R3: Borrowing books"""
    
    @patch('library_service.get_patron_borrow_count')
    @patch('library_service.get_book_by_id')
    @patch('library_service.insert_borrow_record')
    @patch('library_service.update_book_availability')
    def test_borrow_available_book(self, mock_update, mock_insert, mock_get_book, mock_count):
        """TC-R3-01: Successfully borrow an available book"""
        mock_get_book.return_value = {
            'id': 1, 'title': 'Test Book', 'available_copies': 3
        }
        mock_count.return_value = 2
        mock_insert.return_value = True
        mock_update.return_value = True
        
        success, message = borrow_book_by_patron("123456", 1)
        
        self.assertTrue(success)
        self.assertIn("Successfully borrowed", message)
        self.assertIn("Due date:", message)
    
    def test_borrow_invalid_patron_id_non_numeric(self):
        """TC-R3-02: Attempt to borrow with non-numeric patron ID"""
        success, message = borrow_book_by_patron("ABC123", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid patron ID. Must be exactly 6 digits.")
    
    def test_borrow_invalid_patron_id_wrong_length(self):
        """TC-R3-03: Attempt to borrow with wrong length patron ID"""
        success, message = borrow_book_by_patron("12345", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid patron ID. Must be exactly 6 digits.")
    
    @patch('library_service.get_book_by_id')
    def test_borrow_nonexistent_book(self, mock_get_book):
        """TC-R3-04: Attempt to borrow a book not in catalog"""
        mock_get_book.return_value = None
        
        success, message = borrow_book_by_patron("123456", 999)
        
        self.assertFalse(success)
        self.assertEqual(message, "Book not found.")
    
    @patch('library_service.get_book_by_id')
    def test_borrow_unavailable_book(self, mock_get_book):
        """TC-R3-05: Attempt to borrow when no copies available"""
        mock_get_book.return_value = {
            'id': 1, 'title': 'Test Book', 'available_copies': 0
        }
        
        success, message = borrow_book_by_patron("123456", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "This book is currently not available.")
    
    @patch('library_service.get_patron_borrow_count')
    @patch('library_service.get_book_by_id')
    def test_borrow_exceeds_limit(self, mock_get_book, mock_count):
        """TC-R3-06: Attempt to borrow when patron has reached limit"""
        mock_get_book.return_value = {
            'id': 1, 'title': 'Test Book', 'available_copies': 3
        }
        mock_count.return_value = 6
        
        success, message = borrow_book_by_patron("123456", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "You have reached the maximum borrowing limit of 5 books.")


class TestR4_ReturningBooks(unittest.TestCase):
    """Test cases for R4: Returning books"""
    
    @patch('library_service.calculate_late_fee_for_book')
    @patch('library_service.update_book_availability')
    @patch('library_service.update_borrow_record_return_date')
    @patch('library_service.get_patron_borrowed_books')
    @patch('library_service.get_book_by_id')
    def test_return_book_no_late_fee(self, mock_get_book, mock_borrowed, mock_update_return, mock_update_avail, mock_fee):
        """TC-R4-01: Return a book on time with no late fee"""
        mock_get_book.return_value = {'id': 1, 'title': 'Test Book'}
        mock_borrowed.return_value = [{'book_id': 1}]
        mock_update_return.return_value = True
        mock_update_avail.return_value = True
        mock_fee.return_value = {'fee_amount': 0.0}
        
        success, message = return_book_by_patron("123456", 1)
        
        self.assertTrue(success)
        self.assertEqual(message, "Returned successfully")
    
    @patch('library_service.calculate_late_fee_for_book')
    @patch('library_service.update_book_availability')
    @patch('library_service.update_borrow_record_return_date')
    @patch('library_service.get_patron_borrowed_books')
    @patch('library_service.get_book_by_id')
    def test_return_book_with_late_fee(self, mock_get_book, mock_borrowed, mock_update_return, mock_update_avail, mock_fee):
        """TC-R4-02: Return a book late with late fee"""
        mock_get_book.return_value = {'id': 1, 'title': 'Test Book'}
        mock_borrowed.return_value = [{'book_id': 1}]
        mock_update_return.return_value = True
        mock_update_avail.return_value = True
        mock_fee.return_value = {'fee_amount': 3.50}
        
        success, message = return_book_by_patron("123456", 1)
        
        self.assertTrue(success)
        self.assertIn("Late fee: $3.50", message)
    
    def test_return_invalid_patron_id(self):
        """TC-R4-03: Attempt to return with invalid patron ID"""
        success, message = return_book_by_patron("ABC", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid patron ID. Must be exactly 6 digits.")
    
    @patch('library_service.get_book_by_id')
    def test_return_nonexistent_book(self, mock_get_book):
        """TC-R4-04: Attempt to return a book not in catalog"""
        mock_get_book.return_value = None
        
        success, message = return_book_by_patron("123456", 999)
        
        self.assertFalse(success)
        self.assertEqual(message, "Book not found.")
    
    @patch('library_service.get_patron_borrowed_books')
    @patch('library_service.get_book_by_id')
    def test_return_book_not_borrowed(self, mock_get_book, mock_borrowed):
        """TC-R4-05: Attempt to return a book not borrowed by patron"""
        mock_get_book.return_value = {'id': 1, 'title': 'Test Book'}
        mock_borrowed.return_value = [{'book_id': 2}]
        
        success, message = return_book_by_patron("123456", 1)
        
        self.assertFalse(success)
        self.assertEqual(message, "Book not borrowed by patron")


class TestR5_CalculateLateFee(unittest.TestCase):
    """Test cases for R5: Calculating late fees"""
    
    @patch('library_service.get_db_connection')
    def test_calculate_fee_on_time(self, mock_conn):
        """TC-R5-01: Calculate fee for book returned on time"""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        borrow_date = datetime.now() - timedelta(days=10)
        due_date = datetime.now() + timedelta(days=4)
        return_date = datetime.now()
        
        mock_cursor.fetchone.return_value = {
            'patron_id': '123456',
            'book_id': 1,
            'borrow_date': borrow_date.isoformat(),
            'due_date': due_date.isoformat(),
            'return_date': return_date.isoformat()
        }
        
        result = calculate_late_fee_for_book("123456", 1)
        
        self.assertEqual(result['fee_amount'], 0.0)
        self.assertEqual(result['days_overdue'], 0)
        self.assertEqual(result['status'], 'On time')
    
    @patch('library_service.get_db_connection')
    def test_calculate_fee_3_days_overdue(self, mock_conn):
        """TC-R5-02: Calculate fee for book 3 days overdue"""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        borrow_date = datetime.now() - timedelta(days=17)
        due_date = datetime.now() - timedelta(days=3)
        return_date = datetime.now()
        
        mock_cursor.fetchone.return_value = {
            'patron_id': '123456',
            'book_id': 1,
            'borrow_date': borrow_date.isoformat(),
            'due_date': due_date.isoformat(),
            'return_date': return_date.isoformat()
        }
        
        result = calculate_late_fee_for_book("123456", 1)
        
        self.assertEqual(result['fee_amount'], 1.50)  # 3 days * $0.50
        self.assertEqual(result['days_overdue'], 3)
        self.assertEqual(result['status'], 'Overdue')
    
    @patch('library_service.get_db_connection')
    def test_calculate_fee_10_days_overdue(self, mock_conn):
        """TC-R5-03: Calculate fee for book 10 days overdue"""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        borrow_date = datetime.now() - timedelta(days=24)
        due_date = datetime.now() - timedelta(days=10)
        return_date = datetime.now()
        
        mock_cursor.fetchone.return_value = {
            'patron_id': '123456',
            'book_id': 1,
            'borrow_date': borrow_date.isoformat(),
            'due_date': due_date.isoformat(),
            'return_date': return_date.isoformat()
        }
        
        result = calculate_late_fee_for_book("123456", 1)
        
        # First 7 days: 7 * $0.50 = $3.50
        # Next 3 days: 3 * $1.00 = $3.00
        # Total: $6.50
        self.assertEqual(result['fee_amount'], 6.50)
        self.assertEqual(result['days_overdue'], 10)
    
    @patch('library_service.get_db_connection')
    def test_calculate_fee_max_cap(self, mock_conn):
        """TC-R5-04: Calculate fee capped at $15.00"""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        borrow_date = datetime.now() - timedelta(days=50)
        due_date = datetime.now() - timedelta(days=36)
        return_date = datetime.now()
        
        mock_cursor.fetchone.return_value = {
            'patron_id': '123456',
            'book_id': 1,
            'borrow_date': borrow_date.isoformat(),
            'due_date': due_date.isoformat(),
            'return_date': return_date.isoformat()
        }
        
        result = calculate_late_fee_for_book("123456", 1)
        
        # Should be capped at $15.00
        self.assertEqual(result['fee_amount'], 15.00)
        self.assertEqual(result['days_overdue'], 36)
    
    def test_calculate_fee_invalid_patron_id(self):
        """TC-R5-05: Calculate fee with invalid patron ID"""
        result = calculate_late_fee_for_book("ABC", 1)
        
        self.assertEqual(result['fee_amount'], 0.0)
        self.assertEqual(result['status'], 'Invalid patron ID')
    
    @patch('library_service.get_db_connection')
    def test_calculate_fee_no_record(self, mock_conn):
        """TC-R5-06: Calculate fee when no borrow record exists"""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        result = calculate_late_fee_for_book("123456", 1)
        
        self.assertEqual(result['fee_amount'], 0.0)
        self.assertEqual(result['status'], 'No borrow record')


class TestR6_SearchBooks(unittest.TestCase):
    """Test cases for R6: Searching books"""
    
    @patch('library_service.get_all_books')
    def test_search_by_title_partial_match(self, mock_get_all):
        """TC-R6-01: Search by title with partial match"""
        mock_get_all.return_value = [
            {'isbn': '9780134685991', 'title': 'Effective Java', 'author': 'Joshua Bloch'},
            {'isbn': '9780132350884', 'title': 'Clean Code', 'author': 'Robert Martin'},
            {'isbn': '9780201616224', 'title': 'The Pragmatic Programmer', 'author': 'Hunt Thomas'}
        ]
        
        results = search_books_in_catalog("Java", "title")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Effective Java')
    
    @patch('library_service.get_all_books')
    def test_search_by_author_partial_match(self, mock_get_all):
        """TC-R6-02: Search by author with partial match"""
        mock_get_all.return_value = [
            {'isbn': '9780134685991', 'title': 'Effective Java', 'author': 'Joshua Bloch'},
            {'isbn': '9780132350884', 'title': 'Clean Code', 'author': 'Robert Martin'}
        ]
        
        results = search_books_in_catalog("Martin", "author")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['author'], 'Robert Martin')
    
    @patch('library_service.get_all_books')
    def test_search_by_isbn_exact_match(self, mock_get_all):
        """TC-R6-03: Search by ISBN with exact match"""
        mock_get_all.return_value = [
            {'isbn': '9780134685991', 'title': 'Effective Java', 'author': 'Joshua Bloch'}
        ]
        
        results = search_books_in_catalog("9780134685991", "isbn")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['isbn'], '9780134685991')
    
    @patch('library_service.get_all_books')
    def test_search_case_insensitive(self, mock_get_all):
        """TC-R6-04: Search is case-insensitive"""
        mock_get_all.return_value = [
            {'isbn': '9780134685991', 'title': 'Effective Java', 'author': 'Joshua Bloch'}
        ]
        
        results = search_books_in_catalog("EFFECTIVE", "title")
        
        self.assertEqual(len(results), 1)
    
    def test_search_empty_term(self):
        """TC-R6-05: Search with empty search term"""
        results = search_books_in_catalog("", "title")
        
        self.assertEqual(len(results), 0)
    
    def test_search_none_term(self):
        """TC-R6-06: Search with None search term"""
        results = search_books_in_catalog(None, "title")
        
        self.assertEqual(len(results), 0)
    
    @patch('library_service.get_all_books')
    def test_search_no_results(self, mock_get_all):
        """TC-R6-07: Search returns no results"""
        mock_get_all.return_value = [
            {'isbn': '9780134685991', 'title': 'Effective Java', 'author': 'Joshua Bloch'}
        ]
        
        results = search_books_in_catalog("NonexistentBook", "title")
        
        self.assertEqual(len(results), 0)


class TestR7_PatronStatusReport(unittest.TestCase):
    """Test cases for R7: Patron Status Report"""
    
    @patch('library_service.calculate_late_fee_for_book')
    @patch('library_service.get_db_connection')
    @patch('library_service.get_patron_borrowed_books')
    def test_patron_status_with_borrowed_books(self, mock_borrowed, mock_conn, mock_fee):
        """TC-R7-01: Get status for patron with borrowed books"""
        mock_borrowed.return_value = [
            {
                'book_id': 1,
                'title': 'Test Book 1',
                'author': 'Author 1',
                'borrow_date': '2024-10-01',
                'due_date': '2024-10-15'
            }
        ]
        mock_fee.return_value = {'fee_amount': 2.50, 'days_overdue': 5}
        
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        report = get_patron_status_report("123456")
        
        self.assertEqual(report['patron_id'], "123456")
        self.assertEqual(report['number_borrowed_books'], 1)
        self.assertEqual(report['total_late_fees'], 2.50)
        self.assertEqual(len(report['borrowed_books']), 1)
    
    def test_patron_status_invalid_id(self):
        """TC-R7-02: Get status with invalid patron ID"""
        report = get_patron_status_report("ABC")
        
        self.assertEqual(report, {})
    
    @patch('library_service.get_db_connection')
    @patch('library_service.get_patron_borrowed_books')
    def test_patron_status_no_borrowed_books(self, mock_borrowed, mock_conn):
        """TC-R7-03: Get status for patron with no borrowed books"""
        mock_borrowed.return_value = []
        
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        report = get_patron_status_report("123456")
        
        self.assertEqual(report['patron_id'], "123456")
        self.assertEqual(report['number_borrowed_books'], 0)
        self.assertEqual(report['total_late_fees'], 0.0)
        self.assertEqual(len(report['borrowed_books']), 0)
    
    @patch('library_service.calculate_late_fee_for_book')
    @patch('library_service.get_db_connection')
    @patch('library_service.get_patron_borrowed_books')
    def test_patron_status_multiple_fees(self, mock_borrowed, mock_conn, mock_fee):
        """TC-R7-04: Get status for patron with multiple overdue books"""
        mock_borrowed.return_value = [
            {'book_id': 1, 'title': 'Book 1', 'author': 'Author 1', 'borrow_date': '2024-10-01', 'due_date': '2024-10-15'},
            {'book_id': 2, 'title': 'Book 2', 'author': 'Author 2', 'borrow_date': '2024-09-20', 'due_date': '2024-10-04'}
        ]
        mock_fee.side_effect = [
            {'fee_amount': 2.50, 'days_overdue': 5},
            {'fee_amount': 5.00, 'days_overdue': 10}
        ]
        
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        report = get_patron_status_report("123456")
        
        self.assertEqual(report['number_borrowed_books'], 2)
        self.assertEqual(report['total_late_fees'], 7.50)


if __name__ == '__main__':
    unittest.main()