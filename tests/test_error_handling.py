#!/usr/bin/env python3
"""
Test Error Handling & Retry Logic
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from retry_utils import (
    retry_with_backoff,
    safe_api_call,
    ErrorCollector,
    RetryableAPICall
)


class TestRetryLogic(unittest.TestCase):
    """Test retry decorator and utilities"""
    
    def test_retry_success_on_first_attempt(self):
        """Should succeed immediately without retries"""
        call_count = [0]
        
        @retry_with_backoff(max_attempts=3)
        def always_succeeds():
            call_count[0] += 1
            return "success"
        
        result = always_succeeds()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 1)
    
    def test_retry_success_after_failures(self):
        """Should retry and eventually succeed"""
        call_count = [0]
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        def succeeds_on_third_try():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = succeeds_on_third_try()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)
    
    def test_retry_exhaustion(self):
        """Should raise exception after all retries exhausted"""
        call_count = [0]
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        def always_fails():
            call_count[0] += 1
            raise ValueError("Permanent failure")
        
        with self.assertRaises(ValueError):
            always_fails()
        
        self.assertEqual(call_count[0], 3)
    
    def test_retry_with_specific_exceptions(self):
        """Should only retry specific exceptions"""
        call_count = [0]
        
        @retry_with_backoff(max_attempts=3, exceptions=(ValueError,), initial_delay=0.1)
        def raises_wrong_exception():
            call_count[0] += 1
            raise TypeError("Wrong exception type")
        
        with self.assertRaises(TypeError):
            raises_wrong_exception()
        
        # Should fail immediately, not retry
        self.assertEqual(call_count[0], 1)


class TestSafeAPICall(unittest.TestCase):
    """Test safe API call wrapper"""
    
    def test_safe_call_success(self):
        """Should return result on success"""
        def api_func(value):
            return value * 2
        
        result = safe_api_call(api_func, 5)
        self.assertEqual(result, 10)
    
    def test_safe_call_failure_returns_default(self):
        """Should return default value on failure"""
        def failing_func():
            raise Exception("API error")
        
        result = safe_api_call(failing_func, default=[])
        self.assertEqual(result, [])
    
    def test_safe_call_with_custom_default(self):
        """Should return custom default value"""
        def failing_func():
            raise Exception("Error")
        
        result = safe_api_call(failing_func, default={"status": "error"})
        self.assertEqual(result, {"status": "error"})


class TestErrorCollector(unittest.TestCase):
    """Test error collector for batch operations"""
    
    def test_no_errors(self):
        """Should handle zero errors"""
        collector = ErrorCollector()
        
        self.assertFalse(collector.has_errors())
        self.assertEqual(collector.count(), 0)
        self.assertEqual(collector.report(), "No errors")
    
    def test_collect_errors(self):
        """Should collect multiple errors"""
        collector = ErrorCollector()
        
        collector.add("Operation 1", ValueError("Error 1"))
        collector.add("Operation 2", TypeError("Error 2"))
        
        self.assertTrue(collector.has_errors())
        self.assertEqual(collector.count(), 2)
    
    def test_error_report(self):
        """Should generate error report"""
        collector = ErrorCollector()
        
        collector.add("Test 1", Exception("Fail 1"))
        collector.add("Test 2", Exception("Fail 2"))
        
        report = collector.report()
        
        self.assertIn("2 errors", report)
        self.assertIn("Test 1", report)
        self.assertIn("Test 2", report)
    
    def test_raise_if_errors(self):
        """Should raise if errors exist"""
        collector = ErrorCollector()
        collector.add("Test", Exception("Error"))
        
        with self.assertRaises(RuntimeError):
            collector.raise_if_errors()


class TestRetryableAPICall(unittest.TestCase):
    """Test retryable API call context manager"""
    
    def test_context_manager_success(self):
        """Should log success"""
        with RetryableAPICall("Test operation") as call:
            result = "success"
            call.success(result)
        
        self.assertEqual(call.result, "success")
        self.assertIsNone(call.error)
    
    def test_context_manager_failure(self):
        """Should handle failure"""
        with self.assertRaises(Exception):
            with RetryableAPICall("Test operation", max_attempts=1):
                raise Exception("API failed")


if __name__ == '__main__':
    # Run tests
    unittest.main()
