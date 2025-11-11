"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books, get_patron_borrowed_books,
    get_db_connection

)

from services.payment_service import PaymentGateway

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed > 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    
    Implements R4 as per requirements
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    #Check if book borrowed
    active_borrows = get_patron_borrowed_books(patron_id) or []
    matching = [r for r in active_borrows if r.get('book_id') == book_id]
    if not matching:
        return False, "Book not borrowed by patron"
    
    #Update return date
    now = datetime.now()
    success = update_borrow_record_return_date(patron_id, book_id, now)
    if not success:
        return False, "Could not record return"
    
    #Update available copies
    ok = update_book_availability(book_id, 1)
    if not ok:
        return False, "Could not update availability"
    
    #Calculate late fee
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    fee_amount = fee_info.get('fee_amount', 0.0)

    if fee_amount > 0:
        return True, f"Returned successfully. Late fee: ${fee_amount:.2f}"
    else:
        return True, "Returned successfully"

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fees for a specific book.
    
    Implements R5 as per requirements 
    
    
    return { // return the calculated values
        'fee_amount': 0.00,
        'days_overdue': 0,
        'status': 'Late fee calculation not implemented'
    }
    """

    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {'fee_amount': 0.0, 'days_overdue': 0, 'status': 'Invalid patron ID'}
    
    conn = None
    try:
        conn = get_db_connection()
        curs = conn.cursor()
        curs.execute('''
                     SELECT id, patron_id, book_id, borrow_date, due_date, return_date
                     FROM borrow_records
                     WHERE patron_id = ? AND book_id = ?
                     ORDER BY id DESC
                     LIMIT 1
                     ''', (patron_id, book_id))
        row = curs.fetchone()
    finally:
        if conn:
            conn.close()
    
    if not row:
        return {'fee_amount': 0.0, 'days_overdue': 0, 'status': 'No borrow record'}
    
    def parse_date(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        try:
            return datetime.fromisoformat(val)
        except Exception:
            for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
                try:
                    return datetime.strptime(val, fmt)
                except Exception:
                    continue
        return None
    
    borrow_date = parse_date(row['borrow_date'])
    due_date = parse_date(row['due_date'])
    return_date = parse_date(row['return_date'])

    if due_date is None and borrow_date is not None:
        due_date = borrow_date + timedelta(days=14)

    comparison_date = return_date or datetime.now()

    if not due_date:
        return {'fee_amount': 0.0, 'days_overdue': 0, 'status': 'No due date'}
    
    days_overdue = (comparison_date.date() - due_date.date()).days
    days_overdue = max(0, days_overdue)

    fee = 0.0
    if days_overdue > 0:
        first_seven_days = min(days_overdue, 7)
        after_seven_days = max(0, days_overdue - 7)
        fee = first_seven_days * 0.5 + after_seven_days * 1.0
        if fee > 15.0:
            fee = 15.0

    return {
        'fee_amount': round(fee, 2),
        'days_overdue': days_overdue,
        'status': 'Overdue' if days_overdue > 0 else 'On time'
    }

def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    
    Implements R6 as per requirements
    """
    if search_term is None:
        return []
    
    search = str(search_term).strip()
    if search == "":
        return []
    
    books = get_all_books() or []
    search_lower = search.lower()

    results = []
    if search_type == "isbn":
        results = [b for b in books if b.get('isbn') == search]
    elif search_type == "title":
        results = [b for b in books if search_lower in (b.get('title') or "").lower()]
    elif search_type == "author":
        results = [b for b in books if search_lower in (b.get('author') or "").lower()]
    else:
        results = [b for b in books if search_lower in (b.get('title') or "").lower() or search_lower in (b.get('author') or "").lower()]

    return results

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    
    Implements R7 as per requirements
    """
    
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {}
    
    active_borrow = get_patron_borrowed_books(patron_id) or []

    borrowed_books = []
    total_fees = 0.0

    for rec in active_borrow:
        b_id = rec.get('book_id')
        fee_info = calculate_late_fee_for_book(patron_id, b_id)
        fee = fee_info.get('fee_amount', 0.0)
        total_fees += fee
        borrowed_books.append({
            'book_id': b_id,
            'title': rec.get('title'),
            'author': rec.get('author'),
            'borrow_date': rec.get('borrow_date'),
            'due_date': rec.get('due_date'),
            'days_overdue': fee_info.get('days_overdue', 0),
            'current_fee': fee
        })
    
    history = []
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
                    SELECT br.id, br.book_id, br.borrow_date, br.due_date, br.return_date, b.title, b.author
                    FROM borrow_records br
                    JOIN books b on br.book_id = b.id
                    WHERE br.patron_id = ? AND br.return_date IS NOT NULL
                    ORDER BY br.return_date DESC
                    ''', (patron_id,))
        rows = cur.fetchall()
        for r in rows:
            history.append({
                'record_id': r['id'],
                'book_id': r['book_id'],
                'title': r['title'],
                'author': r['author'],
                'borrow_date': (datetime.fromisoformat(r['borrow_date']) if isinstance(r['borrow_date'], str) else r['borrow_date']),
                'borrow_date': (datetime.fromisoformat(r['due_date']) if isinstance(r['due_date'], str) else r['due_date']),
                'borrow_date': (datetime.fromisoformat(r['return_date']) if isinstance(r['return_date'], str) else r['return_date']),                
            })
    finally:
        if conn:
            conn.close()

    return {
        'patron_id': patron_id,
        'borrowed_books': borrowed_books,
        'number_borrowed_books': len(borrowed_books),
        'total_late_fees': round(total_fees, 2),
        'borrow_history': history
    }

def pay_late_fees(patron_id: str, book_id: int, payment_gateway: PaymentGateway = None) -> Tuple[bool, str, Optional[str]]:
    """
    Process payment for late fees using external payment gateway.
    
    NEW FEATURE FOR ASSIGNMENT 3: Demonstrates need for mocking/stubbing
    This function depends on an external payment service that should be mocked in tests.
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book with late fees
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str, transaction_id: Optional[str])
        
    Example for you to mock:
        # In tests, mock the payment gateway:
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123", "Success")
        success, msg, txn = pay_late_fees("123456", 1, mock_gateway)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits.", None
    
    # Calculate late fee first
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    
    # Check if there's a fee to pay
    if not fee_info or 'fee_amount' not in fee_info:
        return False, "Unable to calculate late fees.", None
    
    fee_amount = fee_info.get('fee_amount', 0.0)
    
    if fee_amount <= 0:
        return False, "No late fees to pay for this book.", None
    
    # Get book details for payment description
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found.", None
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process payment through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN THEIR TESTS!
    try:
        success, transaction_id, message = payment_gateway.process_payment(
            patron_id=patron_id,
            amount=fee_amount,
            description=f"Late fees for '{book['title']}'"
        )
        
        if success:
            return True, f"Payment successful! {message}", transaction_id
        else:
            return False, f"Payment failed: {message}", None
            
    except Exception as e:
        # Handle payment gateway errors
        return False, f"Payment processing error: {str(e)}", None


def refund_late_fee_payment(transaction_id: str, amount: float, payment_gateway: PaymentGateway = None) -> Tuple[bool, str]:
    """
    Refund a late fee payment (e.g., if book was returned on time but fees were charged in error).
    
    NEW FEATURE FOR ASSIGNMENT 3: Another function requiring mocking
    
    Args:
        transaction_id: Original transaction ID to refund
        amount: Amount to refund
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate inputs
    if not transaction_id or not transaction_id.startswith("txn_"):
        return False, "Invalid transaction ID."
    
    if amount <= 0:
        return False, "Refund amount must be greater than 0."
    
    if amount > 15.00:  # Maximum late fee per book
        return False, "Refund amount exceeds maximum late fee."
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process refund through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN YOUR TESTS!
    try:
        success, message = payment_gateway.refund_payment(transaction_id, amount)
        
        if success:
            return True, message
        else:
            return False, f"Refund failed: {message}"
            
    except Exception as e:
        return False, f"Refund processing error: {str(e)}"