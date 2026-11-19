"""Real-process tests: these start the sample API and verify recovery."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server import Pipeline, diagnose, redact


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': '', 'CREATE_GITHUB_ISSUES': 'false'})
        self.env.start()
        self.temp = tempfile.TemporaryDirectory()
        self.pipeline = Pipeline(Path(self.temp.name))

    def tearDown(self):
        self.pipeline.close()
        self.temp.cleanup()
        self.env.stop()

    def test_healthy_release_replaces_previous_process(self):
        first = self.pipeline.deploy()
        old_process = self.pipeline.active['process']
        second = self.pipeline.deploy()
        self.assertEqual(first['status'], 'healthy')
        self.assertEqual(second['status'], 'healthy')
        self.assertIsNotNone(old_process.poll())
        self.assertTrue(self.pipeline.healthy(self.pipeline.active))
        self.assertEqual(len(self.pipeline.releases), 1)

    def test_both_failures_restore_real_healthy_service_and_save_ticket(self):
        self.pipeline.deploy()
        original = self.pipeline.active
        for fault in ('config', 'crash'):
            with self.subTest(fault=fault):
                result = self.pipeline.deploy(fault)
                self.assertEqual(result['status'], 'rolled_back')
                self.assertIs(self.pipeline.active, original)
                self.assertTrue(self.pipeline.healthy(original))
                self.assertTrue(result['ticket']['body'])
                self.assertEqual(len(self.pipeline.releases), 1)
        self.assertEqual(len(self.pipeline.history()), 3)
        reopened = Pipeline(self.temp.name)
        self.assertEqual(reopened.history()[0]['status'], 'rolled_back')

    def test_first_failed_release_does_not_claim_rollback(self):
        result = self.pipeline.deploy('config')
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(self.pipeline.active)
        self.assertEqual(len(self.pipeline.releases), 0)

    def test_startup_failure_restores_previous_release(self):
        self.pipeline.deploy()
        with patch.object(self.pipeline, 'start_release', side_effect=RuntimeError('Port bind failed')):
            result = self.pipeline.deploy()
        self.assertEqual(result['status'], 'rolled_back')
        self.assertIn('Port bind failed', result['logs'])

    def test_concurrent_deployment_is_rejected(self):
        self.pipeline.lock.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                self.pipeline.deploy()
        finally:
            self.pipeline.lock.release()

    def test_diagnosis_survives_provider_failure_and_redacts_secrets(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-secret'}):
            self.assertNotIn('test-secret', redact('key test-secret'))
            with patch('server.request_json', side_effect=OSError('offline')):
                result = diagnose('DATABASE_URL missing')
        self.assertIn('LLM request failed', result['source'])
        self.assertIn('DATABASE_URL', result['text'])


if __name__ == '__main__':
    unittest.main()
