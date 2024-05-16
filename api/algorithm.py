import os
from googlemaps import Client as GoogleMapsClient
from googlemaps.distance_matrix import distance_matrix
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class Person:
    def __init__(self, name, address, capacity, is_driving=False, is_destination=False):
        """
        Initializes a person or a destination.

        :param name: The name of the person or the name of the destination.
        :param address: The address of the person's home or the destination.
        :param is_driving: A boolean indicating if the person is driving. Defaults to False.
        :param is_destination: A boolean indicating if this instance represents a destination. Defaults to False.
        """
        self.name = name
        self.address = address
        self.is_driving = is_driving
        self.is_destination = is_destination
        if capacity and not is_driving:
            raise ValueError("Non-driving persons cannot have a capacity.")
        self.capacity = capacity


class RoutePlanner:
    def __init__(self, persons, api_key):
        """
        Initializes the Route Planner with a list of Person instances and a Google Maps API key.

        :param persons: A list of Person instances.
        :param api_key: Google Maps API key for fetching distance matrices.
        """
        self.persons = persons
        self.api_key = api_key
        self.destinations = [p.address for p in persons if p.is_destination]
        self.drivers = [p for p in persons if p.is_driving and not p.is_destination]
        self.passengers = [
            p for p in persons if not p.is_driving and not p.is_destination
        ]

    def plan_routes(self):
        """
        Plans routes for all drivers to pick up passengers and head to the destination(s).
        """
        if not self.destinations:
            raise ValueError(
                "At least one destination is required."
            )  # There should only be one destination?
        if not self.drivers:
            raise ValueError("At least one driver is required.")

        # Initialize GoogleDistanceMatrixClient
        google_distance_client = GoogleDistanceMatrixClient(self.api_key)

        # Add origins and destinations
        for driver in self.drivers:
            google_distance_client.add_origin(driver.address)
        for destination in self.destinations:
            google_distance_client.set_destination(destination)

        # Fetch distance matrix
        try:
            dist_matrix = google_distance_client.fetch_distance_matrix()
            # Convert dist_matrix to a format suitable for VRPSolver
            # This step would involve transforming the results from GoogleDistanceMatrixClient
            # into a numerical matrix format expected by VRPSolver.
            # For simplicity, let's assume dist_matrix is already in the correct format.

            # Define vehicle capacities based on the assumption that each vehicle can carry a certain number of passengers.
            vehicle_capacities = [
                driver.capacity for driver in self.drivers
            ]  # Assuming Person has a 'capacity' attribute

            # Initialize and solve the VRP
            vrp_solver = VRPSolver(dist_matrix, len(self.drivers), vehicle_capacities)
            vrp_solver.solve()
        except Exception as e:
            print(f"An error occurred: {str(e)}")


# Missing a solver for "all vehicles begin at one location and end at different locations"
"""
Define a Common Starting Point: Ensure the depot is set as the common starting point for all vehicles. This is already done with "depot": 0 in your code, assuming the first location in your distance matrix is the starting point for all vehicles.
Allow for Multiple End Points: You'll need to modify the VRP setup to allow each vehicle to have its own unique endpoint. This isn't directly supported by the basic VRP model in OR-Tools, but you can simulate it by treating each unique endpoint as a mandatory last stop for each vehicle. This involves setting up "end" nodes for each vehicle and ensuring these nodes are only visited by their respective vehicles.
Here's a conceptual approach to modify your code for Scenario 2:
Step 1: Define end nodes for each vehicle. If you have N locations and M vehicles, you could artificially extend your distance matrix to include M additional rows and columns, representing these end nodes.
Step 2: Adjust the distance matrix to ensure that each vehicle's end node is only reachable by that vehicle, and it's the last node they visit. This might involve setting the distances from all non-end locations to these end nodes appropriately and ensuring the distance from each vehicle's end node to its start node (the depot) is zero or a very small value to close the loop.
Step 3: Modify the capacity and demand settings if necessary to ensure that the vehicles are required to reach these end nodes last.
"""

from typing import List


# Assume that this solves for "all vehicles converge to one location".
class VRPSolver:
    def __init__(self, distance_matrix, vehicle_capacities: List[int]):
        """
        Initializes the VRP Solver.

        :param distance_matrix: A matrix of distances between locations, including the destination.
        :param num_vehicles: The number of vehicles (drivers) available.
        :param vehicle_capacities: A list of capacities for each vehicle.
        """
        self.distance_matrix = distance_matrix
        self.vehicle_capacities = vehicle_capacities
        self.data = {
            "distance_matrix": distance_matrix,
            "vehicle_capacities": vehicle_capacities,
            "depot": 0,  # Assuming the first location in the distance matrix is the destination. Depot is the destination location
        }
        self.manager = None
        self.routing = None
        self.solution = None

    def solve(self):
        """Solves the VRP problem."""
        # Create the routing index manager and Routing Model.
        self.manager = pywrapcp.RoutingIndexManager(
            len(self.data["distance_matrix"]),
            self.data["num_vehicles"],
            self.data["depot"],
        )
        self.routing = pywrapcp.RoutingModel(self.manager)

        # Create and register a transit callback.
        transit_callback_index = self.routing.RegisterTransitCallback(
            lambda from_index, to_index: self.data["distance_matrix"][
                self.manager.IndexToNode(from_index)
            ][self.manager.IndexToNode(to_index)]
        )

        # Define cost of each arc.
        self.routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add Capacity constraint.
        demand_callback_index = self.routing.RegisterUnaryTransitCallback(
            lambda index: 1
        )  # Assuming each passenger represents a demand of 1
        self.routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            self.data["vehicle_capacities"],  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )

        # Solve the problem.
        self.solution = self.routing.SolveWithParameters(search_parameters)
        if self.solution:
            self.print_solution()

    def print_solution(self):
        """Prints solution on console."""
        total_distance = 0
        for vehicle_id in range(self.data["num_vehicles"]):
            index = self.routing.Start(vehicle_id)
            plan_output = "Route for vehicle {}:\n".format(vehicle_id)
            route_distance = 0
            while not self.routing.IsEnd(index):
                plan_output += " {} -> ".format(self.manager.IndexToNode(index))
                previous_index = index
                index = self.solution.Value(self.routing.NextVar(index))
                route_distance += self.routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            plan_output += "{}\n".format(self.manager.IndexToNode(index))
            plan_output += "Distance of the route: {}m\n".format(route_distance)
            print(plan_output)
            total_distance += route_distance
        print("Total Distance of all routes: {}m".format(total_distance))


class GoogleDistanceMatrixClient:
    def __init__(self, api_key):
        self.client = GoogleMapsClient(key=api_key)
        self.origins = []
        self.destination = []

    def add_origin(self, origin):
        """Add a single origin address."""
        self.origins.append(origin)

    def set_destination(self, destination):
        """Set the destination address."""
        self.destination.append(destination)

    def fetch_distance_matrix(self):
        """Fetch the distance matrix from Google's Distance Matrix API using the google maps distance sdk."""
        if not self.origins or not self.destination:
            raise ValueError(
                "Origins and destination must be set before fetching the distance matrix."
            )

        # Use the Google Maps Distance Matrix SDK to fetch the distance matrix
        distance_matrix_result = distance_matrix(
            self.client, self.origins, self.destination, mode="driving"
        )

        # Check the response
        if distance_matrix_result["status"] == "OK":
            results = []
            for origin_index, origin in enumerate(self.origins):
                row = distance_matrix_result["rows"][origin_index]
                distance = row["elements"][0]["distance"]["text"]
                duration = row["elements"][0]["duration"]["text"]
                results.append(
                    f"From {origin} to {self.destination}: {distance}, {duration}"
                )
            return results
        else:
            raise Exception(
                f"Error fetching distance matrix: {distance_matrix_result['status']}"
            )


if __name__ == "__main__":
    google_distance_client = GoogleDistanceMatrixClient(
        os.getenv("GOOGLE_MAPS_API_KEY")
    )
    google_distance_client.add_origin("1600 Amphitheatre Parkway, Mountain View, CA")
    google_distance_client.add_origin("555 California St, San Francisco, CA")
    google_distance_client.add_origin("1 World Way, Los Angeles, CA")
    google_distance_client.add_origin("2001 Point West Way, Sacramento, CA")
    google_distance_client.set_destination("1 Infinite Loop, Cupertino, CA")
    try:
        dist_matrix = google_distance_client.fetch_distance_matrix()
        for result in dist_matrix:
            print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    # Instantiate VRPSolver and set vehicle 1 and 2 as drivers
    vrp_solver = VRPSolver(dist_matrix, [5, 5])
    vrp_solver.set_driver("Vehicle 1")
    vrp_solver.set_driver("Vehicle 2")
