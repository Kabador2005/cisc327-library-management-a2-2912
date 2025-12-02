"""
E2E Tests for Library Management System

Installation:
    pip install pytest playwright
    playwright install chromium

Usage:
    pytest tests/test_e2e.py -v
"""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5000"


def test_add_book_e2e():
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Generate a unique 13-digit ISBN for this test run
        timestamp = int(time.time())
        test_isbn = f"978{timestamp % 10000000000:010d}"
        test_title = "E2E Test Book"
        test_author = "E2E Test Author"
        test_copies = "3"
        
        # Step 1: Navigate to add book page
        page.goto(f"{BASE_URL}/add_book")
        
        # Verify we're on the add book page
        assert "Add New Book" in page.content()
        
        # Step 2: Fill in the form
        page.fill("input[name='title']", test_title)
        page.fill("input[name='author']", test_author)
        page.fill("input[name='isbn']", test_isbn)
        page.fill("input[name='total_copies']", test_copies)
        
        # Step 3: Submit form
        page.click("button[type='submit']")
        
        # Step 4: Wait for navigation/response
        page.wait_for_load_state("networkidle")
        
        # Check for errors
        flash_error = page.locator(".flash-error")
        if flash_error.count() > 0:
            raise AssertionError(f"Form submission failed: {flash_error.inner_text()}")
        
        # Verify success message
        flash_success = page.locator(".flash-success")
        assert flash_success.is_visible(), "Success message should be visible"
        
        flash_text = flash_success.inner_text()
        assert "successfully added" in flash_text.lower()
        assert test_title in flash_text
        
        # Step 5: Navigate to catalog
        if "/catalog" not in page.url:
            page.goto(f"{BASE_URL}/catalog")
            page.wait_for_load_state("networkidle")
        
        # Step 6: Verify the book appears in the catalog
        book_title_cell = page.locator(f"td:has-text('{test_title}')").first
        assert book_title_cell.is_visible(), f"Book title '{test_title}' should be visible in catalog"
        
        book_author_cell = page.locator(f"td:has-text('{test_author}')").first
        assert book_author_cell.is_visible(), f"Author '{test_author}' should be visible in catalog"
        
        book_isbn_cell = page.locator(f"td:has-text('{test_isbn}')").first
        assert book_isbn_cell.is_visible(), f"ISBN '{test_isbn}' should be visible in catalog"
        
        availability = page.locator(f"text={test_copies}/{test_copies} Available").first
        assert availability.is_visible(), f"Availability should be visible"
        
        browser.close()


def test_borrow_book_e2e():
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Use a unique patron ID to avoid hitting borrowing limits
        test_patron_id = f"{int(time.time()) % 1000000:06d}"
        
        # Generate unique book details
        timestamp = int(time.time())
        test_isbn = f"978{timestamp % 10000000000:010d}"
        test_title = "Borrowing Test Book"
        
        # Step 1: Add a book to ensure we have an available book
        page.goto(f"{BASE_URL}/add_book")
        page.fill("input[name='title']", test_title)
        page.fill("input[name='author']", "Test Author")
        page.fill("input[name='isbn']", test_isbn)
        page.fill("input[name='total_copies']", "2")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        
        # Step 2: Navigate to catalog page
        page.goto(f"{BASE_URL}/catalog")
        page.wait_for_load_state("networkidle")
        
        # Step 3: Verify we're on the catalog page
        assert "Book Catalog" in page.content()
        
        # Check that at least one book with available copies exists
        available_status = page.locator(".status-available").first
        assert available_status.is_visible(), "At least one book should be available"
        
        # Step 4: Fill in patron ID for the newly added book
        book_row = page.locator(f"tr:has-text('{test_isbn}')").first
        patron_input = book_row.locator("input[name='patron_id']")
        assert patron_input.is_visible(), "Patron ID input should be visible"
        patron_input.fill(test_patron_id)
        
        # Step 5: Click the borrow button for this specific book
        borrow_button = book_row.locator("button.btn-success:has-text('Borrow')")
        assert borrow_button.is_visible(), "Borrow button should be visible"
        borrow_button.click()
        
        # Step 6: Wait for page to process the request
        page.wait_for_load_state("networkidle")
        
        # Check for errors
        flash_error = page.locator(".flash-error")
        if flash_error.count() > 0:
            raise AssertionError(f"Borrow failed: {flash_error.inner_text()}")
        
        # Verify borrow confirmation message appears
        flash_success = page.locator(".flash-success")
        assert flash_success.is_visible(), "Success flash message should appear"
        
        flash_text = flash_success.inner_text().lower()
        assert "successfully borrowed" in flash_text, "Message should contain 'successfully borrowed'"
        assert "due date" in flash_text, "Message should contain 'due date'"
        
        browser.close()