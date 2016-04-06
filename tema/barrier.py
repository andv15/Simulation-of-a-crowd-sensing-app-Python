"""
Acest modul reprezinta o bariera reentranta.

Arhitectura sistemelor de calcul
Tema 1
Martie 2016

SONEA Andreea 333CB
"""

from threading import Semaphore, Lock

class ReusableBarrierSem(object):
    """
    Bariera reentranta, implementata folosind 2 semafoare.
    """

    def __init__(self, num_threads):
        """
        Constructor.

        @param num_threads: numarul de thread-uri permise in acelasi timp
        """
        self.num_threads = num_threads
        self.count_threads1 = [self.num_threads]
        self.count_threads2 = [self.num_threads]

        # protejam accesarea/modificarea contoarelor
        self.counter_lock = Lock()

        # blocam thread-urile in prima etapa
        self.threads_sem1 = Semaphore(0)

        # blocam thread-urile in a doua etapa
        self.threads_sem2 = Semaphore(0)

    def wait(self):
        """
        Asteapta thread-urile pentru prima si a doua etapa.
        Toate thread-urile trebuie sa treaca de acquire() inainte ca vreunul
        sa revina la bariera.
        """
        self.phase(self.count_threads1, self.threads_sem1)
        self.phase(self.count_threads2, self.threads_sem2)

    def phase(self, count_threads, threads_sem):
        """
        Bariera pentru prima etapa.
        - num_threads-1 thread-uri vor face acquire pe semafor
        - ultimul thread face release de num_threads de ori pe semafor
        - unul din release-uri este pentru el
        """
        with self.counter_lock:
            count_threads[0] -= 1

            # a ajuns la bariera si ultimul thread
            if count_threads[0] == 0:

                # incrementare semafor ce va debloca num_threads thread-uri
                nr_release = 0
                while nr_release < self.num_threads:
                    threads_sem.release()
                    nr_release += 1

                # reseteaza contorul
                count_threads[0] = self.num_threads

        # num_threads-1 threaduri se blocheaza aici
        threads_sem.acquire()
        # contorul semaforului se decrementeaza de num_threads ori
