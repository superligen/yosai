import pytest
from unittest import mock
import datetime

from .doubles import (
    MockAbstractNativeSessionManager,
    MockAbstractValidatingSessionManager,
    MockSession,
    MockSessionManager,
)

from yosai import (
    AbstractValidatingSessionManager,
    DefaultSessionSettings,
    DelegatingSession,
    EventBus,
    ExecutorServiceSessionValidationScheduler,
    ExpiredSessionException,
    IllegalArgumentException,
    SessionEventException,
    StoppableScheduledExecutor,
    StoppedSessionException,
    IllegalStateException,
    ImmutableProxiedSession,
    InvalidSessionException,
    UnknownSessionException,
)


# ----------------------------------------------------------------------------
# AbstractNativeSessionManager 
# ----------------------------------------------------------------------------

def test_ansm_publish_event_succeeds(abstract_native_session_manager):
    """
    unit tested:  publish_event

    test case:  successful publish of event to event bus
    """
    ansm = abstract_native_session_manager
    with mock.patch.object(EventBus, 'publish') as meb_pub:
        meb_pub.return_value = None
        ansm.publish_event('dumbevent')
        meb_pub.assert_called_once_with('dumbevent')

def test_ansm_publish_event_fails(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  publish_event

    test case: 
    when no event_bus is set, raises an exception 
    """
    ansm = abstract_native_session_manager
    monkeypatch.delattr(ansm, '_event_bus')
    with pytest.raises(SessionEventException):
        ansm.publish_event('dumbevent')

def test_ansm_start(abstract_native_session_manager, monkeypatch):
    """
    unit tested:  start 

    test case:
    start calls other methods and doesn't compute anything on its own so 
    not much to test here other than to exercise the code path
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    monkeypatch.setattr(ansm, 'create_session', lambda x: dumbsession) 
    monkeypatch.setattr(ansm, 'apply_session_timeouts', lambda x: None)
    monkeypatch.setattr(ansm, 'on_start', lambda x, y: None)
    monkeypatch.setattr(ansm, 'notify_start', lambda x: None)
    monkeypatch.setattr(ansm, 'create_exposed_session', lambda x, y: dumbsession)

    result = ansm.start('session_context')
    assert result == dumbsession 

def test_ansm_apply_session_timeouts(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  apply_session_timeouts 

    test case:
    confirms that the timeout attributes are set in the session object and 
    that on_change is called
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        ansm.apply_session_timeouts(dumbsession)
        assert (mocky.called and 
                dumbsession.absolute_timeout and 
                dumbsession.idle_timeout)

def test_ansm_get_session_locates(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested: get_session 

    test case:
    lookup_session returns a session, and so create_exposed_session is called
    with it
    """
    ansm = abstract_native_session_manager
    monkeypatch.setattr(ansm, 'lookup_session', lambda x: 'session')
    monkeypatch.setattr(ansm, 'create_exposed_session', lambda x, y: 'ces')
    
    results = ansm.get_session('key')

    assert results == 'ces'  # asserts that it was called
    
def test_ansm_get_session_doesnt_locate(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  get_session

    test case:
    lookup session fails to locate a session and so None is returned
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: None) 
    results = ansm.get_session('key')

    assert results is None
    
def test_ansm_lookup_session(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_session

    test case:
    a basic code path exercise confirming that do_get_session is called 
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'do_get_session', lambda x: 'dgs_called') 
    results = ansm.lookup_session('key')

    assert results == 'dgs_called'

def test_ansm_lookup_required_session_locates(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session finds and returns a session
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: 'session')
    results = ansm.lookup_required_session('key')
    assert results == 'session'  # asserts that it was called
  
def test_ansm_lookup_required_session_failstolocate(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session fails to locate a session, raising an exception instead 
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: None) 
    with pytest.raises(UnknownSessionException):
        ansm.lookup_required_session('key')

def test_ansm_create_exposed_session(abstract_native_session_manager):
    """
    unit tested:  create_exposed_session 

    test case:
    basic codepath exercise
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    result = ansm.create_exposed_session(dumbsession)
    assert isinstance(result, DelegatingSession)

def test_ansm_before_invalid_notification(abstract_native_session_manager):
    """
    unit tested:  before_invalid_notification 

    test case:
    basic codepath exercise
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    result = ansm.before_invalid_notification(dumbsession)
    assert isinstance(result, ImmutableProxiedSession)

def test_ansm_notify_start(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  notify_start 

    test case:
    iterates through the list of listeners, calling each's on_start
    """
    ansm = abstract_native_session_manager
    mocklist = [mock.MagicMock(), mock.MagicMock()]
    monkeypatch.setattr(ansm, 'listeners', mocklist)
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    ansm.notify_start(dumbsession)
    results = (mocklist[0].on_start.called and mocklist[1].on_start.called)
    assert results

def test_ansm_notify_stop(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  notify_stop

    test case:
    iterates through the list of listeners, calling each's on_stop
    """
    ansm = abstract_native_session_manager
    mocklist = [mock.MagicMock(), mock.MagicMock()]
    monkeypatch.setattr(ansm, 'listeners', mocklist)
    monkeypatch.setattr(ansm, 'before_invalid_notification', lambda x: 'bla')
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    ansm.notify_stop(dumbsession)
    results = (mocklist[0].on_stop.called and mocklist[1].on_stop.called)
    assert results

def test_ansm_notify_expiration(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  notify_expiration

    test case:
    iterates through the list of listeners, calling each's on_expiration
    """
    ansm = abstract_native_session_manager
    mocklist = [mock.MagicMock(), mock.MagicMock()]
    monkeypatch.setattr(ansm, 'listeners', mocklist)
    monkeypatch.setattr(ansm, 'before_invalid_notification', lambda x: 'bla')
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    ansm.notify_expiration(dumbsession)
    results = (mocklist[0].on_expiration.called and 
               mocklist[1].on_expiration.called)
    assert results

def test_ansm_get_start_timestamp(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_start_timestamp

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_start_timestamp('sessionkey')
    expected = datetime.datetime(2015, 6, 17, 19, 43, 51, 818810) 
    assert results == expected

def test_ansm_get_last_access_time(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_last_access_time

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_last_access_time('sessionkey')
    expected = datetime.datetime(2015, 6, 17, 19, 45, 51, 818810) 
    assert results == expected

def test_ansm_get_absolute_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_absolute_timeout

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_absolute_timeout('sessionkey')
    expected = datetime.timedelta(minutes=60)
    assert results == expected

def test_ansm_get_idle_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: get_idle_timeout 

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_idle_timeout('sessionkey')
    expected = datetime.timedelta(minutes=15)
    assert results == expected

def test_ansm_set_idle_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_idle_timeout 

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    timeout = datetime.timedelta(minutes=30)
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        ansm.set_idle_timeout('sessionkey123', timeout)
        assert (mocky.called and mock_session.idle_timeout == timeout)

def test_ansm_set_absolute_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_absolute_timeout 

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    timeout = datetime.timedelta(minutes=30)

    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        ansm.set_absolute_timeout('sessionkey123', timeout)
        assert (mocky.called and mock_session.absolute_timeout == timeout)

def test_ansm_touch(patched_abstract_native_session_manager, mock_session):
    """
    unit tested:  touch

    test case:
    basic code exercise, passes through
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        with mock.patch.object(MockSession, 'touch') as touchy:
            ansm.touch('sessionkey123')
            assert (mocky.called and touchy.called)

def test_ansm_get_host(patched_abstract_native_session_manager):
    """
    unit tested:  get_host

    test case:
    basic code exercise, passes through and returns host
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        result = ansm.get_host('sessionkey123')
        assert result == '127.0.0.1'

def test_ansm_get_attribute_keys_results(
        patched_abstract_native_session_manager):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns a tuple contains 3 mock items
    """
    ansm = patched_abstract_native_session_manager
    result = ansm.get_attribute_keys('sessionkey123')
    assert 'attr2' in result  # arbitrary check

def test_ansm_get_attribute_keys_empty(
        patched_abstract_native_session_manager, monkeypatch):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns an empty tuple
    """
    ansm = patched_abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234',
                                                  'attribute_keys': None})()
    monkeypatch.setattr(ansm, 'lookup_required_session', lambda x: dumbsession) 
    result = ansm.get_attribute_keys('sessionkey123')
    assert result == tuple()

def test_ansm_get_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  get_attribute

    test case:
    basic code exercise, passes through and returns an attribute 
    """
    ansm = patched_abstract_native_session_manager
    result = ansm.get_attribute('sessionkey123', 'attr2')
    assert result == 'attrX'

def test_ansm_set_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  set_attribute

    test case:
    sets an attribute 
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        ansm.set_attribute('sessionkey123', attribute_key='attr321', value=321)
        mocksession = ansm.lookup_required_session('bla')
        assert (mocky.called and 
                'attr321' in mocksession.session)

def test_ansm_set_attribute_removes(
        patched_abstract_native_session_manager):
    """
    unit tested:  set_attribute

    test case:
    calling set_attribute without a value results in the removal of an attribute 
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(ansm, 'remove_attribute') as mock_ra:
        ansm.set_attribute('sessionkey123', attribute_key='attr1')
        assert mock_ra.called

def test_ansm_remove_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  remove_attribute

    test case:  
    successfully removes an attribute
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        result = ansm.remove_attribute('sessionkey123', 'attr3')
        assert result == 3 and mocky.called

def test_ansm_remove_attribute_nothing(patched_abstract_native_session_manager):
    """
    unit tested:  remove_attribute

    test case:  
    removing an attribute that doesn't exist returns None
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky: 
        result = ansm.remove_attribute('sessionkey123', 'attr5')
        assert result is None and not mocky.called

def test_ansm_is_valid(patched_abstract_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    a valid sesion returns True
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(MockAbstractNativeSessionManager, 'check_valid') as mocky: 
        mocky.return_value = True
        result = ansm.is_valid('sessionkey123')
        assert result

def test_ansm_is_valid_raisefalse(patched_abstract_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    an invalid sesion returns False 
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(MockAbstractNativeSessionManager, 'check_valid') as mocky: 
        mocky.side_effect = InvalidSessionException
        result = ansm.is_valid('sessionkey123')
        assert result is False

def test_ansm_stop(patched_abstract_native_session_manager):
    """
    unit tested:  stop

    test case:
    basic method exercise, calling methods and completing
    """
    ansm = patched_abstract_native_session_manager
    mocksession = ansm.lookup_required_session('bla')
    with mock.patch.object(MockSession, 'stop') as stop:
        with mock.patch.object(ansm, 'on_stop') as on_stop:
            with mock.patch.object(ansm, 'notify_stop') as notify_stop:
                with mock.patch.object(ansm, 'after_stopped') as after_stopped:
                    ansm.stop('sessionkey123')
                    stop.assert_called_with()
                    on_stop.assert_called_with(mocksession, 'sessionkey123')
                    notify_stop.assert_called_with(mocksession)
                    after_stopped.assert_called_with(mocksession)
    
def test_ansm_stop_raises(patched_abstract_native_session_manager):
    """
    unit tested:  stop

    test case:
    exception is raised and finally section is executed
    """
    ansm = patched_abstract_native_session_manager
    mocksession = ansm.lookup_required_session('bla')
    with mock.patch.object(MockSession, 'stop') as stop:
        stop.side_effect = InvalidSessionException
        with mock.patch.object(ansm, 'after_stopped') as after_stopped:
            with pytest.raises(InvalidSessionException) as exc:
                ansm.stop('sessionkey123')
            after_stopped.assert_called_with(mocksession)
            assert exc

def test_ansm_on_stop(patched_abstract_native_session_manager):
    """
    unit tested:  on_stop

    test case:
    calls on_change
    """
    ansm = patched_abstract_native_session_manager
    mocksession = ansm.lookup_required_session('bla')
    with mock.patch.object(ansm, 'on_change') as mock_onchange:
        ansm.on_stop(mocksession)
        mock_onchange.assert_called_with(mocksession)

def test_ansm_check_valid_raises(patched_abstract_native_session_manager):
    """
    unit tested:  check_valid

    test case:
    calls lookup_required_session
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(ansm, 'lookup_required_session') as mocky:
        ansm.check_valid('sessionkey123')
        mocky.assert_called_with('sessionkey123')


# ----------------------------------------------------------------------------
# ExecutorServiceSessionValidationScheduler 
# ----------------------------------------------------------------------------

def test_esvs_enable_session_validation(executor_session_validation_scheduler):
    """
    unit tested:  enable_session_validation

    test case:
    interval is set, so service.start() will be invoked and enabled = True 
    """
    
    esvs = executor_session_validation_scheduler
    sse = StoppableScheduledExecutor  # from yosai.concurrency
    with mock.patch.object(sse, 'start') as sse_start:
        esvs.enable_session_validation()
        sse_start.assert_called_with() and esvs.is_enabled


def test_esvs_run(executor_session_validation_scheduler):
    """
    unit tested:  run

    test case:
    session_manager.validate_sessions is invoked
    """
    esvs = executor_session_validation_scheduler

    with mock.patch.object(MockAbstractNativeSessionManager, 
                           'validate_sessions') as sm_vs:
        sm_vs.return_value = None
        esvs.run()
        sm_vs.assert_called_with()

def test_esvs_disable_session_validation(executor_session_validation_scheduler):
    """
    unit tested:  disable_session_validation

    test case:
    interval is set, so service.stop() will be invoked and enabled = False 
    """

    esvs = executor_session_validation_scheduler
    sse = StoppableScheduledExecutor  # from yosai.concurrency
    with mock.patch.object(sse, 'stop') as sse_stop:
        esvs.disable_session_validation()
        sse_stop.assert_called_with() and not esvs.is_enabled

# ----------------------------------------------------------------------------
# AbstractValidatingSessionManager 
# ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'svse,scheduler,scheduler_enabled,expected_result',
    [(True, True, False, True),
     (True, True, True, False),
     (False, True, False, False),
     (True, False, None, True)])
def test_avsm_esvin(abstract_validating_session_manager, monkeypatch,
                    svse, scheduler, scheduler_enabled, expected_result,
                    executor_session_validation_scheduler):
    """
    unit tested:  enable_session_validation_if_necessary

    test case:
    sets a scheduler, defaulting to that from init else enable_session_validation

    I) session_validation_scheduler_enabled = True
       scheduler = self.session_validation_scheduler  
       scheduler.enabled = False 
   II) session_validation_scheduler_enabled = True
       scheduler = self.session_validation_scheduler  
       scheduler.enabled = True 
  III) session_validation_scheduler_enabled = False 
       scheduler = self.session_validation_scheduler
   IV) session_validation_scheduler_enabled = True
       scheduler = None
    """
    myscheduler = None
    if scheduler:
        myscheduler = executor_session_validation_scheduler
        monkeypatch.setattr(myscheduler, '_enabled', scheduler_enabled) 

    avsm = abstract_validating_session_manager
    monkeypatch.setattr(avsm, 'session_validation_scheduler', myscheduler)
    monkeypatch.setattr(avsm, 'session_validation_scheduler_enabled', svse) 

    with mock.patch.object(AbstractValidatingSessionManager,
                           'enable_session_validation') as avsm_esv:
        avsm_esv.return_value = None
        avsm.enable_session_validation_if_necessary()
        assert avsm_esv.called == expected_result

@pytest.mark.parametrize('expected_result', [None, 'retrieved'])
def test_avsm_dogetsession(abstract_validating_session_manager, monkeypatch,
                           expected_result):
    """
    unit tested: do_get_session

    test case:
    enable_session_validation_if_necessary is called
    validate will be called if retrieve_session returns a session
    session is returned
    """
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'enable_session_validation_if_necessary') as avsm_esvin:
        with mock.patch.object(MockAbstractValidatingSessionManager, 
                               'validate') as avsm_validate:
            monkeypatch.setattr(avsm, 'retrieve_session', 
                                lambda x: expected_result) 
            result = avsm.do_get_session('sessionkey123')
            avsm_esvin.assert_called_with()

            assert (avsm_esvin.called and result == expected_result and
                    avsm_validate.called == bool(expected_result))

def test_avsm_create_session(
        abstract_validating_session_manager, monkeypatch):
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'enable_session_validation_if_necessary') as avsm_esvin:
        with mock.patch.object(MockAbstractValidatingSessionManager, 
                               'do_create_session') as avsm_dcs:
            avsm_dcs.return_value = 'session'
            result = avsm.create_session('sessioncontext')
            assert avsm_esvin.called and result == 'session' 

def test_avsm_validate_succeeds(abstract_validating_session_manager):
    """
    unit test:  validate

    test case:
    basic code path exercise, succeeding to call do_validate
    """
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'do_validate') as avsm_dv:
        avsm.validate('testsession', 'sessionkey123')
        avsm_dv.assert_called_with


def test_avsm_validate_expired(abstract_validating_session_manager):
    """
    unit test:  validate

    test case:
    do_validate raises expired session exception, calling on_expiration and
    raising
    """
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'do_validate') as avsm_dv:
        avsm_dv.side_effect = ExpiredSessionException
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'on_expiration') as avsm_oe:
            with pytest.raises(ExpiredSessionException) as excinfo: 
                avsm.validate('testsession', 'sessionkey123')
                assert (avsm_dv.called and avsm_oe.called and 
                        excinfo.type == ExpiredSessionException)


def test_avsm_validate_invalid(abstract_validating_session_manager):
    """
    unit test:  validate

    test case:
    do_validate raises invalid session exception, calling on_invalidation and
    raising
    """
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'do_validate') as avsm_dv:
        avsm_dv.side_effect = InvalidSessionException
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'on_invalidation') as avsm_oi:
            with pytest.raises(InvalidSessionException) as excinfo: 
                avsm.validate('testsession', 'sessionkey123')
                assert (avsm_dv.called and avsm_oi.called and 
                        excinfo.type == InvalidSessionException)

@pytest.mark.parametrize('ese,session_key',
                         [('ExpiredSessionException', None), 
                          (None, 'sessionkey123')])
def test_avsm_on_expiration_onenotset(
        abstract_validating_session_manager, ese, session_key):
    """
    unit tested:  on_expiration

    test case:
        expired_session_exception or session_key are set, but not both
    """
    avsm = abstract_validating_session_manager

    with pytest.raises(IllegalArgumentException):
        avsm.on_expiration(session='testsession',
                           expired_session_exception=ese,
                           session_key=session_key)


def test_avsm_on_expiration_only_session(abstract_validating_session_manager):
    """
    unit tested:  on_expiration

    test case:
        only session is passed as an argument, resulting in on_change called 
    """
    avsm = abstract_validating_session_manager

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'notify_expiration') as avsm_ne:
        
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'after_expired') as avsm_ae:
        
            with mock.patch.object(MockAbstractValidatingSessionManager,
                                   'on_change') as avsm_oc:

                avsm.on_expiration(session='testsession')
                assert (avsm_oc.called and
                        not avsm_ae.called and not avsm_ne.called)


def test_avsm_on_expiration_allset(
        abstract_validating_session_manager, mock_session):
    """
    unit tested:  on_expiration

    test case:
        all parameters are passed, calling on_change, notify_expiration, and 
        after_expired 
    """
    avsm = abstract_validating_session_manager

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'notify_expiration') as avsm_ne:
        
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'after_expired') as avsm_ae:
        
            with mock.patch.object(MockAbstractValidatingSessionManager,
                                   'on_change') as avsm_oc:

                avsm.on_expiration(session=mock_session,
                                   expired_session_exception='ExpiredSessionException',
                                   session_key='sessionkey123')

                assert (avsm_oc.called and avsm_ae.called and avsm_ne.called)


def test_avsm_on_invalidation_esetype(
        abstract_validating_session_manager, mock_session):
    """
    unit tested:  on_invalidation

    test case:
        when an exception of type ExpiredSessionException is passed, 
        on_expiration is called and then method returns
    """
    avsm = abstract_validating_session_manager
    ise = ExpiredSessionException('testing')
    session_key = 'sessionkey123'
    with mock.patch.object(MockAbstractValidatingSessionManager, 
                           'on_expiration') as mock_oe:
        avsm.on_invalidation(session=mock_session,
                             ise=ise,
                             session_key=session_key)
        mock_oe.assert_called_with


def test_avsm_on_invalidation_isetype(
        abstract_validating_session_manager, mock_session):
    """
    unit tested:  on_invalidation

    test case:
        when an exception NOT of type ExpiredSessionException is passed, 
        an InvalidSessionException higher up the hierarchy is assumed 
        and on_stop, notify_stop, and after_stopped are called
    """
    avsm = abstract_validating_session_manager
    ise = InvalidSessionException('testing')
    session_key = 'sessionkey123'
    with mock.patch.object(MockAbstractValidatingSessionManager, 
                           'on_stop') as mock_onstop:
    
        with mock.patch.object(MockAbstractValidatingSessionManager, 
                               'notify_stop') as mock_ns:
        
            with mock.patch.object(MockAbstractValidatingSessionManager, 
                                   'after_stopped') as mock_as:

                avsm.on_invalidation(session=mock_session,
                                     ise=ise,
                                     session_key=session_key)

                mock_onstop.assert_called_with
                mock_ns.assert_called_with
                mock_as.assert_called_with

def test_avsm_do_validate(abstract_validating_session_manager, mock_session):
    """
    unit tested:  do_validate

    test case:
    basic code path exercise where method is called and successfully finishes
    """
    avsm = abstract_validating_session_manager
    assert avsm.do_validate(mock_session) is None


def test_avsm_do_validate_raises(abstract_validating_session_manager):
    """
    unit tested:  do_validate

    test case:
    session.validate is missing, raising an AttributeError which in turn raises
    IllegalStateException
    """
    avsm = abstract_validating_session_manager

    mock_session = type('DumbSession', (object,), {})()

    with pytest.raises(IllegalStateException):
        avsm.do_validate(mock_session)

def test_avsm_create_svs(abstract_validating_session_manager):
    """
    unit tested: create_session_validation_scheduler 

    test case:
    basic codepath exercise that returns a scheduler instance
    """
    avsm = abstract_validating_session_manager
    result = avsm.create_session_validation_scheduler()
    assert isinstance(result, ExecutorServiceSessionValidationScheduler)


def test_avsm_esv_schedulerexists(
    abstract_validating_session_manager, 
        executor_session_validation_scheduler, monkeypatch):
    """
    unit tested: enable_session_validation 

    test case:
    a scheduler is already set, so no new one is created, and two methods 
    called
    """
    avsm = abstract_validating_session_manager
    esvs = executor_session_validation_scheduler

    monkeypatch.setattr(avsm, 'session_validation_scheduler', esvs)

    with mock.patch.object(ExecutorServiceSessionValidationScheduler,
                           'enable_session_validation') as scheduler_esv:
        scheduler_esv.return_value = None
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'after_session_validation_enabled') as asve:
            asve.return_value = None

            avsm.enable_session_validation()

            scheduler_esv.assert_called_with()
            asve.assert_called_with()

def test_avsm_esv_schedulernotexists(
        abstract_validating_session_manager, monkeypatch,
        patched_abstract_native_session_manager): 
    """
    unit tested:  enable_session_validation 

    test case:
    no scheduler is set, so a new one is created and set, and then two 
    methods called
    """
    avsm = abstract_validating_session_manager
    mock_csvs = mock.MagicMock()
    mock_asve = mock.MagicMock()
    monkeypatch.setattr(avsm, 'create_session_validation_scheduler', mock_csvs)
    monkeypatch.setattr(avsm, 'after_session_validation_enabled', mock_asve)

    avsm.enable_session_validation()
    scheduler_esv = avsm.session_validation_scheduler.enable_session_validation
    assert (scheduler_esv.called and mock_asve.called)


def test_avsm_disable_session_validation_withscheduler_succeeds(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    with a scheduler set, the scheduler's disable_session_validation is called
    and succeeds, and then session_validation_scheduler is set to None
    """
    avsm = abstract_validating_session_manager
    scheduler = ExecutorServiceSessionValidationScheduler

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        with mock.patch.object(scheduler, 'disable_session_validation') as dsv:
            dsv.return_value = None

            sched = scheduler(session_manager=avsm, interval=60)
            monkeypatch.setattr(avsm, 'session_validation_scheduler', sched)

            avsm.disable_session_validation()

            assert (mock_bsvd.called and dsv.called and  
                    avsm.session_validation_scheduler is None)

def test_avsm_disable_session_validation_withscheduler_fails(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    with a scheduler set, the scheduler's disable_session_validation is called
    and fails, and then session_validation_scheduler is set to None
    """
    avsm = abstract_validating_session_manager
    
    scheduler = ExecutorServiceSessionValidationScheduler

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        with mock.patch.object(scheduler, 'disable_session_validation') as dsv:
            dsv.side_effect = AttributeError 

            sched = scheduler(session_manager=avsm, interval=60)
            monkeypatch.setattr(avsm, 'session_validation_scheduler', sched)

            avsm.disable_session_validation()

            assert (mock_bsvd.called and dsv.called and  
                    avsm.session_validation_scheduler is None)


def test_avsm_disable_session_validation_without_scheduler(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    without a scheduler set,  only before_session_validation_disabled is called
    """
    avsm = abstract_validating_session_manager

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        avsm.disable_session_validation()

        assert mock_bsvd.called and avsm.session_validation_scheduler is None 

