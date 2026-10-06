"""Attach the current task identity to legitimate state-machine test writes."""

def mutate_as_agent(flow, action, payload):
    payload = dict(payload)
    state = flow.read()
    request = state.get('taskRequest')
    if (payload.get('by') == 'agent' or payload.get('taskId')) and request:
        payload.setdefault('revision', state['revision'])
        # Leave missing-ID running-worker tests unguarded so they still fail.
        if request['status'] in ('queued', 'waiting'):
            payload.setdefault('taskId', request['id'])
    return flow.mutate(action, payload)
