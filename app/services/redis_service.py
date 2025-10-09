# -*- coding):
        self.r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
        # Colas de RQ para los distintos flujos
        self.script_queue = Queue('scripts_queue', connection=self.r)
        self.video_queue = Queue('video_scripts_queue', connection=self.r)
        self.frames_queue = Queue('frames_scripts_queue', connection=self.r)
        self.metadata_queue = Queue('metadata_scripts_queue', connection=self.r)
        self.frontend_queue = Queue('frontend_queue', connection=self.r)

    def get_next_script(self):
        """Obtiene el siguiente script de la cola en Redis (flujo original)."""
        script_data = self.r.blpop("scripts_queue", timeout=0)
        if script_data= script_data[1].decode("utf-8")
            return decoded_data.split(":", 1)
        return None

    def get_next_video_script(self):
        """
        Obtiene el siguiente mensaje de la cola en Redis para conversión de video.
        Se espera el formato= self.r.blpop("video_scripts_queue", timeout=0)
        if script_data= script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3):
        """
        Obtiene el siguiente mensaje de la cola en Redis para conversión de video.
        Se espera el formato= self.r.blpop("frames_scripts_queue", timeout=0)
        if script_data= script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3):
        """
        Obtiene el siguiente mensaje de la cola en Redis para la extraccion de metadatos.
        Se espera el formato= self.r.blpop("metadata_scripts_queue", timeout=0)
        if script_data= script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3, script_id, status):
        """Actualiza el estado del script en Redis."""
        key = "script_status_{}".format(script_id)
        if self.r.exists(key):
            key_type = self.r.type(key)
            if key_type != b'list':
                self.r.delete(key)
        self.r.rpush(key, status)

    def push_result(self, script_id, result):
        """Envía el resultado del script a Redis."""
        self.r.rpush("results_queue_{}".format(script_id), result)

    # --- Métodos para usar RQ ---
    def enqueue_script(self, script_id, script_content):
        """Encola la ejecución de un script como trabajo de RQ."""
        self.script_queue.enqueue(rq_tasks.process_script_task, script_id, script_content)

    def enqueue_graphviz(self, script_id, graphviz_content):
        """Encola la renderización de contenido Graphviz como trabajo de RQ."""
        # Reuses the same script queue since ScriptService now handles both types
        self.script_queue.enqueue(rq_tasks.process_script_task, script_id, graphviz_content)

    def enqueue_video_conversion(self, script_id, script_content, video_id):
        """Encola la conversión de video a audio."""
        self.video_queue.enqueue(rq_tasks.process_video_task, script_id, script_content, video_id)

    def enqueue_frames_extraction(self, script_id, script_content, video_id):
        """Encola la extracción de frames de un video."""
        self.frames_queue.enqueue(rq_tasks.process_frames_task, script_id, script_content, video_id)

    def enqueue_metadata_extraction(self, script_id, script_content, video_id):
        """Encola la extracción de metadatos de un video."""
        self.metadata_queue.enqueue(rq_tasks.process_metadata_task, script_id, script_content, video_id)

    def enqueue_frontend_deployment(
        self, deployment_id, code, port=None, npm=False
    ):
        """Encola el despliegue de un frontend.

        ``code`` puede ser un string HTML o un proyecto npm codificado en base64
        si ``npm`` es ``True``.
        """
        self.frontend_queue.enqueue(
            rq_tasks.deploy_frontend_from_code_task, code, deployment_id, port, npm
        )
