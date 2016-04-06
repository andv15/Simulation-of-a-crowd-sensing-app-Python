"""
Acest modul reprezinta un device.

Arhitectura sistemelor de calcul
Tema 1
Martie 2016

SONEA Andreea 333CB
"""

from threading import Event, Thread, Lock
from barrier import ReusableBarrierSem


class Device(object):
    """
    Clasa ce reprezinta un device.
    """

    def __init__(self, device_id, sensor_data, supervisor):
        """
        Constructor.

        @type device_id: Integer
        @param device_id: id unic al device-ului; intre 0 si N-1

        @type sensor_data: List of (Integer, Float)
        @param sensor_data: o lista continand (location, data) masurata de
            acest device

        @type supervisor: Supervisor
        @param supervisor: infrastructura de testare
        """
        self.device_id = device_id
        self.sensor_data = sensor_data
        self.supervisor = supervisor

        # eveniment de sosire scripturi
        self.script_received = Event()

        # lista de scripturi primite
        self.scripts = []

        # lock pentru fiecare locatie
        self.lock_locations = []

        # bariera pentru trecerea la urmatorul timepoint
        self.barrier = ReusableBarrierSem(0)

        # thread-ul master al device-ului
        self.thread = DeviceThread(self)

    def __str__(self):
        """
        Afiseaza informatii despre device.

        @rtype: String
        @return: un string continand id-ul device-ului
        """
        return "Device %d" % self.device_id

    def setup_devices(self, devices):
        """
        Seteaza device-urile inainte ca simularea sa inceapa.

        @type devices: lista de Device
        @param devices: lista continand toate device-urile
        """
        # creaza o bariera reentranta
        barrier = ReusableBarrierSem(len(devices))

        # primul device
        if self.device_id == 0:
            nr_locations = 0

            # afla numarul de locatii
            for i in range(len(devices)):
                for location in devices[i].sensor_data.keys():
                    if location > nr_locations:
                        nr_locations = location
            # sunt numerotate intre 0 si nr_location
            nr_locations += 1

            # creaza lock-uri pentru fiecare locatie
            for i in range(nr_locations):
                lock_location = Lock()
                self.lock_locations.append(lock_location)

            for i in range(len(devices)):
                # distribuie bariera fiecarui device
                devices[i].barrier = barrier

                # adauga lock-ul pentru toate locatiile in fiecare device
                for j in range(nr_locations):
                    devices[i].lock_locations.append(self.lock_locations[j])

                # porneste thread-ul master al fiecarui device
                devices[i].thread.start()

    def assign_script(self, script, location):
        """
        Asigneaza un script device-ului.

        @type script: Script
        @param script: script ce se va executa la fiecare timepoint;
            None daca timepoint-ul curent s-a terminat

        @type location: Integer
        @param location: locatia pentru care script-ul este interesat
        """
        if script is not None:
            # adauga script-ul primit in lista
            self.scripts.append((script, location))
        else:
            # anunta ca s-au primit toate script-urile pe timepoint-ul curent
            self.script_received.set()

    def get_data(self, location):
        """
        Returneaza valoarea poluarii pe care acest device o are pentru locatia
        data.

        @type location: Integer
        @param location: locatia pentru care se cere valoarea poluarii

        @rtype: Float
        @return: valoarea poluarii
        """
        if location in self.sensor_data:
            return self.sensor_data[location]
        else:
            return None

    def set_data(self, location, data):
        """
        Seteaza valoarea poluarii pentru acest device pentru locatia data.

        @type location: Integer
        @param location: locatia pentru care se retine informatia

        @type data: Float
        @param data: valoarea poluarii
        """
        if location in self.sensor_data:
            self.sensor_data[location] = data

    def shutdown(self):
        """
        Termina thread-ul master al device-ului. Metoda este invpcata de
        tester. Trebuie sa fie blocata pana cand toate thread-urile worker
        ale device-ului au terminat.
        """
        self.thread.join()



class DeviceThread(Thread):
    """
    Clasa ce implementeaza thread-ul master al device-ului.
    """

    def __init__(self, device):
        """
        Constructor.

        @type device: Device
        @param device: device-ul ce detine acest thread
        """
        Thread.__init__(self, name="Device Thread %d" % device.device_id)
        self.device = device


    def run(self):
        # lista cu workerii ce rezolva scripturile primite
        workers = []

        while True:
            # afla vecinii
            neighbours = self.device.supervisor.get_neighbours()
            if neighbours is None:
                break

            # asteapta ca toate scripturile timepont-ului curent sa fie primite
            self.device.script_received.wait()
            self.device.script_received.clear()

            # creaza un worker pentru fiecare script
            for (script, location) in self.device.scripts:
                workers.append(Worker(self.device, script,
                                        location, neighbours))

            # porneste thread-urile worker
            for i in range(len(workers)):
                workers[i].start()

            # asteapta sa termine thread-urile worker
            for i in range(len(workers)):
                workers[i].join()

            # reinitializeaza lista cu thread-urile worker
            workers = []

            # asteapta toate thread-urile master pentru a trece la
            # urmatorul timepoint
            self.device.barrier.wait()



class Worker(Thread):
    """
    Clasa ce implementeaza thread worker ce rezolva scripturi.
    """

    def __init__(self, device, script, location, neighbours):
        """
        Constructor.

        @type device: Device
        @param device: device-ul ce detine acest thread
        @param script: script-ul ce va fi rulat
        @param location: locatia
        @param neighbours: vecinii din timepoint-ul curent
        """
        Thread.__init__(self, name="Device Thread %d" % device.device_id)
        self.device = device
        self.script = script
        self.location = location
        self.neighbours = neighbours

    def solve_script(self, script, location, neighbours):
        """
        Ruleaza un script si retine datele obtinute.

        @param script: script-ul ce va fi rulat
        @param location: locatia pentru care cere informatii
        @param neighbours: vecinii din timepoint-ul curent
        """
        # acapareaza lock-ul pentru locatie
        self.device.lock_locations[location].acquire()

        script_data = []

        # colecteaza date de la vecini pentru locatie
        for device in neighbours:
            data = device.get_data(location)
            if data is not None:
                script_data.append(data)

        # adauga si datele proprii daca le detine
        data = self.device.get_data(location)
        if data is not None:
            script_data.append(data)

        if script_data != []:
            # ruleaza script-ul pe datele colectate
            result = script.run(script_data)

            # actualizeaza datele vecinilor
            for device in neighbours:
                device.set_data(location, result)

            # actualizeaza datele proprii
            self.device.set_data(location, result)

        # elibereaza lock-ul pentru locatie
        self.device.lock_locations[location].release()

    def run(self):
        # rezolva script-ul primit
        self.solve_script(self.script, self.location, self.neighbours)
