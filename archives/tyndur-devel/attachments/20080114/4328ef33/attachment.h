#ifndef _CDI_FS_H_
#define _CDI_FS_H_

#include "types.h"
#include "cdi.h"
#include "cdi/lists.h"

#define CDI_FS_META_NONE       0 /* -/- */
#define CDI_FS_META_MODE       1 /* r/w */
#define CDI_FS_META_OWNER      2 /* r/w */
#define CDI_FS_META_GROUP      3 /* r/w */
#define CDI_FS_META_SIZE       4 /* r/- */
#define CDI_FS_META_USEDBLOCKS 5 /* r/- */
#define CDI_FS_META_CREATETIME 6 /* r/- */
#define CDI_FS_META_ACCESSTIME 7 /* r/- */
#define CDI_FS_META_CHANGETIME 8 /* r/- */
#define CDI_FS_META_ATTRIBUTES 9 /* r/- */

#define CDI_FS_TYPE_NONE     0
#define CDI_FS_TYPE_FILE     1
#define CDI_FS_TYPE_DIR      2
#define CDI_FS_TYPE_FIF0     3
#define CDI_FS_TYPE_LIFO     4
#define CDI_FS_TYPE_BLOCKDEV 5
#define CDI_FS_TYPE_CHARDEV  6
#define CDI_FS_TYPE_SYMLINK  7
#define CDI_FS_TYPE_SOCKET   8

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
   *  @return 0 = Success
   */
  int setmeta(const char *path,int which);
  /**
   * Gets meta data of a file/dir/pipe/etc
   *  @param path Path to file/dir/pipe/etc
   *  @param which Which meta information to get
   *  @return 0 = Success
   */
  int getmeta(const char *path,int which);
};

void cdi_fs_driver_init(struct cdi_fs_driver* driver);
void cdi_fs_driver_destroy(struct cdi_fs_driver* driver);
void cdi_fs_driver_register(struct cdi_fs_driver* driver);

#endif
