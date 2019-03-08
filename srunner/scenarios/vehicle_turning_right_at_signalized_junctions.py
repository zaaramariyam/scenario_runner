#!/usr/bin/env python

# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Non-signalized junctions: crossing negotiation

The hero vehicle is passing through a junction without traffic lights
and encounters another vehicle passing across the junction.
"""

import py_trees
import sys
from agents.navigation.local_planner import RoadOption

from srunner.scenariomanager.atomic_scenario_behavior import *
from srunner.scenariomanager.atomic_scenario_criteria import *
from srunner.scenarios.basic_scenario import *


VEHICLE_TURNING_RIGHT_AT_SIGNALS_SCENARIOS = [
    "VehicleTurningRightAtSignalizedJunctions",
]


class VehicleTurningRightAtSignalizedJunctions(BasicScenario):

    """
    Implementation class for
    'Non-signalized junctions: crossing negotiation' scenario,
    Traffic Scenario 10.
    """

    category = "VehicleTurningRightAtSignals"

    timeout = 120

    # ego vehicle parameters
    _ego_vehicle_driven_distance = 100

    # other vehicle
    _other_actor_max_brake = 1.0
    _other_actor_target_velocity = 25

    def __init__(self, world, ego_vehicle, other_actors, town, randomize=False, debug_mode=False, config=None):
        """
        Setup all relevant parameters and create scenario
        """
        self._traffic_light = CarlaDataProvider.get_next_traffic_light(ego_vehicle, False)

        if self._traffic_light is None:
            print("No traffic light for the given location found")
            sys.exit(-1)

        self._traffic_light.set_state(carla.TrafficLightState.Green)
        self._traffic_light.set_green_time(self.timeout)

        super(VehicleTurningRightAtSignalizedJunctions, self).__init__("VehicleTurningRightAtSignalizedJunctions",
                                                       ego_vehicle,
                                                       other_actors,
                                                       town,
                                                       world,
                                                       debug_mode)

    def _create_behavior(self):
        """
        After invoking this scenario, it will wait for the user
        controlled vehicle to enter the start region,
        then make a traffic participant to accelerate
        until it is going fast enough to reach an intersection point.
        at the same time as the user controlled vehicle at the junction.
        Once the user controlled vehicle comes close to the junction,
        the traffic participant accelerates and passes through the junction.
        After 60 seconds, a timeout stops the scenario.
        """

        # Creating leaf nodes
        location, _ = get_location_in_distance(self.ego_vehicle, 10)
        start_condition = InTriggerDistanceToLocation(self.ego_vehicle, location, 15.0)

        target_location = get_intersection(self.ego_vehicle, self.other_actors[0])

        sync_arrival = SyncArrival(self.other_actors[0], self.ego_vehicle, target_location)
        sync_arrival_stop = InTriggerDistanceToNextIntersection(self.other_actors[0], 10)

        # Selecting straight path at intersection
        target_waypoint = generate_target_waypoint(
            self.other_actors[0].get_world().get_map().get_waypoint(
                self.other_actors[0].get_location()), 1)

        # Generating waypoint list till next intersection
        plan = []
        wp_choice = target_waypoint.next(1.0)
        while len(wp_choice) == 1:
            target_waypoint = wp_choice[0]
            plan.append((target_waypoint, RoadOption.LANEFOLLOW))
            wp_choice = target_waypoint.next(5.0)

        keep_velocity_other = WaypointFollower(self.other_actors[0], self._other_actor_target_velocity, plan=plan)
        stop_other_trigger = DriveDistance(self.other_actors[0], 40)

        stop_other = StopVehicle(
            self.other_actors[0],
            self._other_actor_max_brake)

        end_condition = DriveDistance(self.ego_vehicle, 20)

        # Creating non-leaf nodes
        scenario_sequence = py_trees.composites.Sequence()
        sync_arrival_parallel = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)
        keep_velocity_other_parallel = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)

        # Building tree
        scenario_sequence.add_child(start_condition)
        scenario_sequence.add_child(sync_arrival_parallel)
        scenario_sequence.add_child(keep_velocity_other_parallel)
        scenario_sequence.add_child(stop_other)
        scenario_sequence.add_child(end_condition)
        sync_arrival_parallel.add_child(sync_arrival)
        sync_arrival_parallel.add_child(sync_arrival_stop)
        keep_velocity_other_parallel.add_child(keep_velocity_other)
        keep_velocity_other_parallel.add_child(stop_other_trigger)

        return scenario_sequence

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        criteria = []

        # Adding checks for ego vehicle
        collision_criterion_ego = CollisionTest(self.ego_vehicle)
        driven_distance_criterion = DrivenDistanceTest(self.ego_vehicle,
                                                       self._ego_vehicle_driven_distance,
                                                       distance_acceptable=90,
                                                       optional=True)
        criteria.append(collision_criterion_ego)
        criteria.append(driven_distance_criterion)

        return criteria
