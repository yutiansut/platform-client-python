import pytest

from neuromation import Resources
from neuromation.cli.command_handlers import ModelHandlerOperations
from neuromation.client import Image
from neuromation.client.jobs import NetworkPortForwarding


@pytest.fixture()
def alice_model():
    return ModelHandlerOperations('alice')


class TestNormalCases:

    def test_model_submit(self, alice_model, partial_mocked_model):
        alice_model.train('ubuntu:tf_2.0_beta',
                          'storage:///data/set.txt',
                          'storage://~/results/result1.txt',
                          0, 1, 100, False,
                          '', partial_mocked_model, http=None, ssh=None)
        partial_mocked_model().train.assert_called_once()
        partial_mocked_model().train.assert_called_with(
            image=Image(
                image='ubuntu:tf_2.0_beta',
                command=''),
            resources=Resources(
                memory=100,
                gpu=0,
                cpu=1.0,
                shm=False
            ),
            network=None,
            dataset=f'storage://alice/data/set.txt',
            results=f'storage://alice/results/result1.txt'
        )

    def test_model_submit_with_http(self, alice_model, partial_mocked_model):
        alice_model.train('ubuntu:tf_2.0_beta',
                          'storage:///data/set.txt',
                          'storage://~/results/result1.txt',
                          0, 1, 100, False,
                          '', partial_mocked_model, http=8888, ssh=None)
        partial_mocked_model().train.assert_called_once()
        partial_mocked_model().train.assert_called_with(
            image=Image(
                image='ubuntu:tf_2.0_beta',
                command=''),
            resources=Resources(
                memory=100,
                gpu=0,
                cpu=1.0,
                shm=False
            ),
            network=NetworkPortForwarding(
                {'http': 8888}
            ),
            dataset=f'storage://alice/data/set.txt',
            results=f'storage://alice/results/result1.txt'
        )

    def test_model_submit_with_ssh(self, alice_model, partial_mocked_model):
        alice_model.train('ubuntu:tf_2.0_beta',
                          'storage:///data/set.txt',
                          'storage://~/results/result1.txt',
                          0, 1, 100, False,
                          '', partial_mocked_model, http=None, ssh=8888)
        partial_mocked_model().train.assert_called_once()
        partial_mocked_model().train.assert_called_with(
            image=Image(
                image='ubuntu:tf_2.0_beta',
                command=''),
            resources=Resources(
                memory=100,
                gpu=0,
                cpu=1.0,
                shm=False
            ),
            network=NetworkPortForwarding(
                {'ssh': 8888}
            ),
            dataset=f'storage://alice/data/set.txt',
            results=f'storage://alice/results/result1.txt'
        )

    def test_model_submit_with_ssh_and_http(self,
                                            alice_model,
                                            partial_mocked_model):
        alice_model.train('ubuntu:tf_2.0_beta',
                          'storage:///data/set.txt',
                          'storage://~/results/result1.txt',
                          0, 1, 100, False,
                          '', partial_mocked_model, http=7878, ssh=8888)
        partial_mocked_model().train.assert_called_once()
        partial_mocked_model().train.assert_called_with(
            image=Image(
                image='ubuntu:tf_2.0_beta',
                command=''),
            resources=Resources(
                memory=100,
                gpu=0,
                cpu=1.0,
                shm=False
            ),
            network=NetworkPortForwarding(
                {'ssh': 8888, 'http': 7878}
            ),
            dataset=f'storage://alice/data/set.txt',
            results=f'storage://alice/results/result1.txt'
        )

    def test_model_submit_wrong_src(self, alice_model, partial_mocked_model):
        with pytest.raises(ValueError):
            alice_model.train('ubuntu:tf_2.0_beta',
                              '/data/set.txt',
                              'storage://~/results/result1.txt',
                              0, 1, 100, False,
                              '', partial_mocked_model, http=None, ssh=None)
        assert partial_mocked_model().train.call_count == 0

    def test_model_submit_wrong_dst(self, alice_model, partial_mocked_model):
        with pytest.raises(ValueError):
            alice_model.train('ubuntu:tf_2.0_beta',
                              'storage://~/data/set.txt',
                              'http://results/result1.txt',
                              0, 1, 100, False,
                              '', partial_mocked_model,
                              http=None,
                              ssh=None)
        assert partial_mocked_model().train.call_count == 0