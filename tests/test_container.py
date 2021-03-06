import aioxmpp
import pytest
from asynctest import MagicMock, CoroutineMock

from spade.behaviour import OneShotBehaviour
from spade.container import Container
from spade.message import Message
from tests.test_behaviour import wait_for_behaviour_is_killed
from tests.utils import make_connected_agent


def test_use_container():
    container = Container()
    container.reset()

    agent = make_connected_agent(use_container=True)

    assert agent.container == Container()

    assert container.has_agent(str(agent.jid))
    assert container.get_agent(str(agent.jid)) == agent

    agent.stop()


def test_use_container_false():
    container = Container()
    container.reset()

    agent = make_connected_agent(use_container=False)

    assert agent.container is None

    assert not container.has_agent(str(agent.jid))

    with pytest.raises(KeyError):
        container.get_agent(str(agent.jid))

    agent.stop()


def test_send_message_with_container():
    class FakeReceiverAgent:
        def __init__(self):
            self.jid = "fake_receiver_agent@server"

        def set_container(self, c): pass

    class SendBehaviour(OneShotBehaviour):
        async def run(self):
            message = Message(to="fake_receiver_agent@server")
            await self.send(message)
            self.kill()

    container = Container()
    container.reset()
    fake_receiver_agent = FakeReceiverAgent()
    container.register(fake_receiver_agent)

    fake_receiver_agent.dispatch = MagicMock()

    agent = make_connected_agent(use_container=True)
    agent.start(auto_register=False)

    agent.aiothread.client = MagicMock()
    agent.client.send = CoroutineMock()
    behaviour = SendBehaviour()
    agent.add_behaviour(behaviour)

    wait_for_behaviour_is_killed(behaviour)

    assert agent.client.send.await_count == 0

    assert fake_receiver_agent.dispatch.call_count == 1
    assert str(fake_receiver_agent.dispatch.call_args[0][0].to) == "fake_receiver_agent@server"

    agent.stop()


def test_send_message_to_outer_with_container():
    class SendBehaviour(OneShotBehaviour):
        async def run(self):
            message = Message(to="to@outerhost")
            await self.send(message)
            self.kill()

    container = Container()
    container.reset()

    agent = make_connected_agent(use_container=True)
    agent.start(auto_register=False)

    behaviour = SendBehaviour()
    behaviour._xmpp_send = CoroutineMock()
    agent.add_behaviour(behaviour)

    wait_for_behaviour_is_killed(behaviour)

    assert container.has_agent(str(agent.jid))
    assert not container.has_agent("to@outerhost")

    assert behaviour._xmpp_send.await_count == 1
    msg_arg = behaviour._xmpp_send.await_args[0][0]
    assert msg_arg.to == aioxmpp.JID.fromstr("to@outerhost")

    agent.stop()
