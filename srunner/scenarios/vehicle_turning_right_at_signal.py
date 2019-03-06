#!/usr/bin/env python

#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Non-signalized junctions: crossing negotiation:

The hero vehicle is passing through a junction without traffic lights
And encounters another vehicle passing across the junction.
"""

import py_trees
import carla
import sys

from srunner.scenariomanager.atomic_scenario_behavior import *
from srunner.scenariomanager.atomic_scenario_criteria import *
from srunner.scenariomanager.timer import TimeOut
from srunner.scenarios.basic_scenario import *
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider

VEHICLE_TURNING_RIGHT_AT_SIGNAL_SCENARIOS = ["VehicleTurningRightAtSignal"]

class VehicleTurningRightAtSignal(BasicScenario):

    """
    Implementation class for
    'Vehicle turning right at signalized junction' scenario,
    Traffic Scenario 09.
    """
    category = "VehicleTurningRightAtSignal"

    timeout = 80

    def __init__(self, world, ego_vehicle, other_actors, town, randomize=False, debug_mode=False):
        """
        Setup all relevant parameters and create scenario
        and instantiate scenario manager
        """
        self._traffic_light = CarlaDataProvider.get_next_traffic_light(ego_vehicle, False)

        if self._traffic_light is None:
            print("No traffic light for the given location found")
            sys.exit(-1)

        self._traffic_light.set_state(carla.TrafficLightState.Green)
        self._traffic_light.set_green_time(self.timeout)

        super(VehicleTurningRightAtSignal, self).__init__(
            "VehicleTurningRightAtSignal",
            ego_vehicle,
            other_actors,
            town,
            world,
            debug_mode)

        # if debug_mode:
        #     py_trees.logging.level = py_trees.logging.Level.DEBUG

    def _create_behavior(self):
        """
        The ego vehicle is passing through a junction and a traffic participant
        takes a right turn on to the ego vehicle's lane. The ego vehicle has to
        navigate the scenario without collision with the participant and cross
        the junction.
        """

        # Creating leaf nodes
        
        start_trigger_location, _ = get_location_in_distance(self.ego_vehicle, 2)
        start_other_trigger = InTriggerDistanceToLocation(
            self.ego_vehicle, start_trigger_location, 1)

        location = get_intersection(self.ego_vehicle, self.other_actors[0])
        sync_arrival = SyncArrival(self.other_actors[0], self.ego_vehicle, location)
        pass_through_trigger = InTriggerDistanceToNextIntersection(self.other_actors[0], 10)

        turn_right = TurnVehicle(self.other_actors[0], 30, 1)

        end_location, _ = get_location_in_distance(self.other_actors[0], 100)
        end_condition = InTriggerDistanceToLocation(
            self.ego_vehicle, end_location, 10.0)
        # end_condition = DriveDistance(self.ego_vehicle, 200)

        # Creating non-leaf nodes
        scenario_sequence = py_trees.composites.Sequence()
        sync_arrival_parallel = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)

        # Building tree
        scenario_sequence.add_child(start_other_trigger)
        scenario_sequence.add_child(sync_arrival_parallel)
        scenario_sequence.add_child(turn_right)
        scenario_sequence.add_child(WaypointFollower(self.other_actors[0], 20))
        scenario_sequence.add_child(end_condition)
        sync_arrival_parallel.add_child(sync_arrival)
        sync_arrival_parallel.add_child(pass_through_trigger)

        return scenario_sequence

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        criteria = []

        # Adding checks for ego vehicle
        collision_criterion_ego = CollisionTest(self.ego_vehicle)
        criteria.append(collision_criterion_ego)

        # Add approriate checks for other vehicles
        for vehicle in self.other_actors:
            collision_criterion = CollisionTest(vehicle)
            criteria.append(collision_criterion)

        return criteria

