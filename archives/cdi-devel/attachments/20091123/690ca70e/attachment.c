/* cdi-idc.h */

struct cdi_memory_area;
struct cdi_idc_endpoint;

cdi_list_t cdi_idc_list_endpoints(void);
cdi_device_t cdi_idc_endpoint_type(struct cdi_idc_endpoint* ep);


typedef enum {
    CDI_MEM_PHYS_CONTIGUOUS,
} cdi_malloc_flags_t;

struct cdi_memory_area* cdi_idc_malloc(size_t size, cdi_malloc_flags_t flags);
void cdi_idc_free(struct cdi_memory_area* p);


typedef void (*cdi_idc_handler_t)(
    struct cdi_device* dev,
    void* metadata,
    size_t metadata_size,
    struct cdi_memory_area *data);

int cdi_idc_send_message(
    struct cdi_idc_endpoint* endpoint,
    void* metadata,
    size_t metadata_size,
    struct cdi_memory_area* data);
void cdi_idc_set_message_handler(cdi_idc_handler_t handler);


/* cdi-osdep.h */

struct cdi_memory_area {
    /* Common part */
    size_t size;
    void* vaddr;
    uintptr_t paddr;

    /* OS specific part */
    int shm_id;
};

struct cdi_idc_endpoint {
    pid_t driver_pid;
    int device_id;
};


/* cdi-mixer.h */

struct cdi_mixer_driver {
    int (*play)(int device_id, int channel, struct cdi_memory_area* data);
};


/* cdi-audio.h */

typedef enum {
    CDI_AUDIO_PLAY,
    CDI_AUDIO_RECORD,
    CDI_AUDIO_SETVOLUME,
} cdi_audio_cmd_t;

struct cdi_audio_idc_header {
    cdi_audio_cmd_t cmd;
};

static void cdi_audio_idc_handler(
    struct cdi_device* dev,
    void* metadata,
    size_t metadata_size,
    struct cdi_memory_area *data)
{
    struct cdi_audio_idc_header* header = metadata;
    switch (header->cmd) {
        case PLAY:
            cdi_audio_play(dev, data->vaddr, data->size);
            break;
    }
}
