import numpy as np
import trimesh


class OptimizarAlturaDeCapa:
    # Factor de calidad. Es el maximo stepover admitido en mm
    q_factor = 0.4

    def __init__(self, mesh, limits_inf, limits_sup, angles, height):
        min_layer_height = 0.05
        max_layer_height = 0.3
        # max-min tiene que ser divisible por step
        step_layer_height = 0.05
        # Mesh de trimesh
        self.mesh = mesh
        # Limite inferior de cada triangulo (np-array)
        self.limits_inf = limits_inf
        # Limite superior de cada trinangulo (np-array)
        self.limits_sup = limits_sup
        # Altura del modelo
        self.height = height
        # Tangente del angulo formado entre (n_x,n_y,0) y (0,0,n_z). Con este, se calcula el volumen de error (stepover) (np-array)
        self.angles = angles
        # Perfil de altura de capa
        self.layers_profile = None
        # Parametros de Optimizacion
        self.min_layer_height = min_layer_height
        self.max_layer_height = max_layer_height
        self.step_layer_height = step_layer_height

    @classmethod
    def import_from_geometrymodel(cls, geometrymodel):
        mesh = trimesh.load_mesh(geometrymodel.file.path)
        triangles_count = len(mesh.triangles)
        # Completamos los arrays:
        limits_inf = np.empty(triangles_count)
        limits_sup = np.empty(triangles_count)
        # Llenamos el array de limites
        for trig_index, trig in enumerate(mesh.triangles):
            limits_inf[trig_index] = min([trig[i][2] for i in range(0, 3)])
            limits_sup[trig_index] = max([trig[i][2] for i in range(0, 3)])
        # Llenamos el array de angulos
        angles = np.empty(triangles_count)
        for trig_index, trig in enumerate(mesh.face_normals):
            hip = np.sqrt(trig[0] ** 2 + trig[1] ** 2)
            if hip != 0:
                angles[trig_index] = abs(trig[2]) / hip
            else:
                # Tangente de infinito. Un número lo suficientemente bajo, para que sea descartado naturalmente
                angles[trig_index] = 0
        # Calculamos la altura
        height = max(limits_sup) - min(limits_inf)
        return cls(mesh, limits_inf, limits_sup, angles, height)

    # Transladamos el mesh al origen
    def translate_to_origin(self):
        initial_z = min(self.limits_inf)
        self.limits_inf += -initial_z
        self.limits_sup += -initial_z
        self.mesh.apply_translation([0, 0, -initial_z])

    # Crea un array con las alturas de capa adaptivas. Es decir, la suma sobre este array, da la altura del objeto
    def create_layer_profile(self):
        initial_z = min(self.limits_inf)
        final_z = max(self.limits_sup)
        layers_profile = []
        # Comenzamos con el barrido sobre el objeto
        actual_z = initial_z
        while actual_z <= final_z:
            current_layer_height = self.max_layer_height
            condition_satisfied = False
            # print("Analizando capa {}".format(actual_z))
            # Mientras que el error no sea menor al especificado, vamos reduciendo la altura de capa actual
            while not condition_satisfied:
                '''
                Verifica la altura de capa actual la condicion? Para ello, buscamos todos los triangulos
                que intersequen (o esten contenidos entre) a los planos z=actual_z y z=current_layer_height+actual_z
                Con ello, tomamos el más inclinado (ie, de mayor angulo; y por lo tanto, mayor tangente),
                y calculamos el stepover. Si no satisface la conidicion, reducimos la altura de capa
                '''
                trig_index = np.intersect1d(np.flatnonzero(self.limits_inf < current_layer_height + actual_z),
                                            np.flatnonzero(self.limits_sup > actual_z))
                if len(trig_index) == 0:
                    condition_satisfied = True
                for index in trig_index:
                    stepover = self.angles[index] * current_layer_height
                    # print(stepover)
                    if stepover > self.q_factor:
                        # No alcanza. Reducimos la altura de capa
                        if current_layer_height - self.step_layer_height > self.min_layer_height:
                            current_layer_height = current_layer_height - self.step_layer_height
                        else:
                            # Alcanzamos el minimo :(
                            current_layer_height = self.min_layer_height
                            condition_satisfied = True
                        break
                    else:
                        condition_satisfied = True
            # Ya tenemos lista esta capa. Guardamos la altura, y pasamos a la proxima
            layers_profile.append(current_layer_height)
            # Borramos los triangulos cuyo limite sup, esta por debajo de actual_z+current_layer_height
            delete_index = np.flatnonzero(self.limits_sup < current_layer_height + actual_z)
            self.limits_sup = np.delete(self.limits_sup, delete_index)
            self.limits_inf = np.delete(self.limits_inf, delete_index)
            self.angles = np.delete(self.angles, delete_index)
            actual_z += current_layer_height
        self.layers_profile = layers_profile
        return layers_profile

        # A partir del perfil de altura de capa, calculamos la altura de capa sugerida

    def calculate_layer_height(self):
        '''
        Consideramos el promedio sobre el perfil de altura de capa
        '''
        if self.layers_profile == None:
            print("Calcular primero el perfil de altura de capa")
            return False
        layer_height = np.mean(self.layers_profile)
        # Modificador para objetos muy chicos, de modo, que tenga al menos 50 capas
        layer_height = min(layer_height, self.height / 50)
        # Computamos la altura de capa
        altura_de_capa_permitido = np.arange(0, (
                    self.max_layer_height - self.min_layer_height) / self.step_layer_height + self.step_layer_height) * self.step_layer_height + self.min_layer_height
        return altura_de_capa_permitido[np.abs(altura_de_capa_permitido - layer_height).argmin()]
