#ifndef _CDI_FS_H_
#define _CDI_FS_H_

#include "types.h"
#include "cdi.h"
#include "cdi/lists.h"

#define CDI_FS_META_NONE       0 /* -/- Invalid Meta read        */
#define CDI_FS_META_MODE       1 /* r/w Get/Set permissions      */
#define CDI_FS_META_OWNER      2 /* r/w Get/Set owner            */
#define CDI_FS_META_GROUP      3 /* r/w Get/Set owner group      */
#define CDI_FS_META_TYPE       4 /* r/- Get file type            */
#define CDI_FS_META_SIZE       5 /* r/- Get file size            */
#define CDI_FS_META_USEDBLOCKS 6 /* r/- Get how many blocks used */
#define CDI_FS_META_CREATETIME 7 /* r/- Get creation time        */
#define CDI_FS_META_ACCESSTIME 8 /* r/- Get time of last access  */
#define CDI_FS_META_CHANGETIME 9 /* r/- Get time if last change  */

#define CDI_FS_ERROR_NONE    0 /* No Error */
#define CDI_FS_ERROR_ONS     1 /* Operation not supported */
#define CDI_FS_ERROR_FNF     2 /* File not found */
#define CDI_FS_ERROR_EOF     3 /* End of file */
#define CDI_FS_ERROR_UNKNOWN 4 /* Unknown error */

typedef enum {
  CDI_FS_TYPE_NONE     = 0, // Invalid file type
  CDI_FS_TYPE_FILE     = 1, // normal file
  CDI_FS_TYPE_DIR      = 2, // Directory
  CDI_FS_TYPE_FIF0     = 3, // First-In-First-Out-Pipe
  CDI_FS_TYPE_LIFO     = 4, // Last-In-First-Out-Pipe (Stack)
  CDI_FS_TYPE_BLOCKDEV = 5, // Block device
  CDI_FS_TYPE_CHARDEV  = 6, // Character device
  CDI_FS_TYPE_SYMLINK  = 7, // Symbolic link, points to another file
  CDI_FS_TYPE_SOCKET   = 8, // Unix socket
  CDI_FS_TYPE_BUFFER   = 9 // Buffer (like file but stored in RAM and will get deleted when closed)
} cdi_filetype_t;

struct cdi_fs_driver {
  struct cdi_driver drv;
  /**
   * Opens a file/pipe/etc and returns file descriptor
   *  @param path Path to file
   *  @return File descriptor (negative = Failure)
   */
  int open(const char *path);
  /**
   * Closes a file
   *  @param fildes File descriptor
   *  @return 0 = Success
   */
  int close(int fildes);
  /**
   * Creates an file/dir/pipe/etc
   *  @param path Path to file
   *  @param type Whether it is a file/dir/etc
   *  @param mode Permissions
   *  @return 0 = Success
   */
  int create(const char *path,int type,mode_t mode);
  /**
   * Removes a file/dir/pipe/etc
   *  @param path Path to dir
   *  @return 0 = Success
   */
  int remove(const char *path);
  /**
   * Puts filenames of files from dir in list
   *  @param path Path to dir
   *  @param content List with filenames
   *  @return 0 = Success
   */
  int listdir(const char *path,cdi_list_t content);
  /**
   * Sets meta data of a file/dir/pipe/etc
   *  @param path Path to file/dir/pipe/etc
   *  @param which Which meta information to set
   *  @param value Value to set as meta
   *  @return 0 = Success
   */
  void setmeta(const char *path,int which,int value);
  /**
   * Gets meta data of a file/dir/pipe/etc
   *  @param path Path to file/dir/pipe/etc
   *  @param which Which meta information to get
   *  @return Meta data
   */
  int getmeta(const char *path,int which);
  /**
   * Reads from an opened file
   *  @param fildes File descriptor of opened file
   *  @return Byte readed
   */
  u8 read(int fildes);
  /**
   * Writes to an opened file
   *  @param fildes File descriptor of opened file
   *  @param byte Byte to write
   */
  void write(int fildes,u8 byte);
};

void cdi_fs_driver_init(struct cdi_fs_driver* driver);
void cdi_fs_driver_destroy(struct cdi_fs_driver* driver);
void cdi_fs_driver_register(struct cdi_fs_driver* driver);
void cdi_fs_seterror(struct cdi_fs_driver* driver,int error);

#endif
