import walkoff.case.subscription as case_subs
from tests.util.servertestcase import ServerTestCase
from walkoff.case.subscription import set_subscriptions, clear_subscriptions
from walkoff.extensions import db
from walkoff.serverdb.casesubscription import CaseSubscription


class TestCaseConfigDatabase(ServerTestCase):
    def tearDown(self):
        clear_subscriptions()
        for case in CaseSubscription.query.all():
            db.session.delete(case)
        db.session.commit()

    def __help_test_init(self, case, name, subscription):
        self.assertIsNotNone(case)
        self.assertEqual(case.name, name)
        self.assertEqual(case.subscriptions, subscription)

    # def test_init(self):
    #     case = CaseSubscription('name')
    #     self.__help_test_init(case, 'name', '[]')
    #
    #     case = CaseSubscription('name', subscriptions=[])
    #     self.__help_test_init(case, 'name', '[]')
    #
    #     test_json = [{'id': 'id1', 'events': ['a', 'b']}, {'id': 'id2', 'events': ['c', 'd']}]
    #     case = CaseSubscription('name', test_json)
    #     self.__help_test_init(case, 'name', json.dumps(test_json))
    #
    # def test_to_from_json(self):
    #     case = CaseSubscription('name')
    #     expected_json = {'id': None, 'name': 'name', 'note': '', 'subscriptions': []}
    #     self.assertDictEqual(case.as_json(), expected_json)
    #     derived_json = CaseSubscription.from_json('name', []).as_json()
    #     self.assertDictEqual(derived_json, expected_json)
    #
    #     case = CaseSubscription('name', subscriptions=[])
    #     expected_json = {'id': None, 'name': 'name', 'note': '', 'subscriptions': []}
    #     self.assertDictEqual(case.as_json(), expected_json)
    #
    #     test_json = [{'id': 'id1', 'events': ['a', 'b']}, {'id': 'id2', 'events': ['c', 'd']}]
    #     case = CaseSubscription('name', test_json)
    #     expected_json = {'name': 'name', 'subscriptions': test_json, "id": None, 'note': ''}
    #     self.assertDictEqual(case.as_json(), expected_json)
    #     derived_json = CaseSubscription.from_json('name', test_json).as_json()
    #     self.assertDictEqual(derived_json, expected_json)

    def test_sync_to_subscriptions(self):
        case1 = [{'id': 'id1', 'events': ['e1', 'e2', 'e3']}, {'id': 'id2', 'events': ['e1']}]
        case2 = [{'id': 'id1', 'events': ['e2', 'e3']}]
        case3 = [{'id': 'id3', 'events': ['e', 'b', 'c']}, {'id': 'id4', 'events': ['d']}]
        case4 = [{'id': 'id1', 'events': ['a', 'b']}]
        cases = {'case1': case1, 'case2': case2}
        set_subscriptions(cases)
        case_db_entry_1 = CaseSubscription('case3', subscriptions=case3)
        case_db_entry_2 = CaseSubscription('case4', subscriptions=case4)
        db.session.add(case_db_entry_1)
        db.session.add(case_db_entry_2)
        db.session.commit()
        CaseSubscription.sync_to_subscriptions()
        self.assertIn('case3', case_subs.subscriptions)
        self.assertIn('case4', case_subs.subscriptions)
        self.assertNotIn('case1', case_subs.subscriptions)
        self.assertNotIn('case2', case_subs.subscriptions)
        self.assertDictEqual(case_subs.subscriptions['case3'], {sub['id']: sub['events'] for sub in case3})
        self.assertDictEqual(case_subs.subscriptions['case4'], {sub['id']: sub['events'] for sub in case4})
