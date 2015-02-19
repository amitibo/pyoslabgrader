GENERAL
------
1) Use the stats file create by the grader to see if there is some test
   that no submission passes. This probably (in my case, always) means
   that there is a bug in that test.

LIST
----
1) Require that the students use the kernel list, and that they should
   include the list head statically (e.g. in the task_struct). This
   is important for Memory tracking (see notes in MEMORY TRACKING).

MEMORY TRACKING
---------------
1) When testing freeing of memory when a process is exited, it is important
   that the os._exit will be tracked. Therefore it is dangerous to turn the
   tracking on and off using start_track() and end_track().
2) When testing freeing of memory when a list of elements is cleared of all
   its elements (MESSAGES lists , TODOS list etc) there might be a problem
   if the list itself is allocated only when the first element is added to
   the list. For example if the todo_struct has a list to track TODOs. if
   the list is created when the first TODO is added, and deleted when the
   process exits, you want be able to test memory handling when the all
   elements are removed. The students can clain (correctly) that this is
   a valid implementation that doesn't leak memory.
