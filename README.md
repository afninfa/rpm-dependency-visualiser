# rpm-dependency-visualiser

Text-based visualisation of your RPM dependency relationships!

Suppose you have a bunch of RPMs in a flat directory like this

```
$ ls -l
total 60
-rw-rw-r-- 1 afni afni 5609 Oct  3 18:49 dummy-a-1.0-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5625 Oct  3 18:53 dummy-b-1.0-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5641 Oct  3 19:03 dummy-c-1.0-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5609 Oct  3 19:04 dummy-d-1.0-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5641 Oct  3 20:57 dummy-e-1.3-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5641 Oct  3 20:57 dummy-f-1.3-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 5625 Oct  3 19:09 dummy-g-2.1-1.x86_64.rpm
-rw-rw-r-- 1 afni afni 3826 Oct  3 21:30 rpmdag.py
```

`rpmdag.py` shows you the DAG in text form

```
$ python3 rpmdag.py . dummy-f-1.3-1.x86_64.rpm
1   dummy-f
2   |  dummy-e
3   |  |  dummy-c
4   |  |  |  dummy-a
5   |  |  |  dummy-b
6   |  |  |  |  dummy-a (already expanded on line 4)
7   |  |  dummy-d
8   |  dummy-g
9   |  |  dummy-c (already expanded on line 3)
```

This means
- `dummy-f` has two dependencies, `dummy-e` and `dummy-g`
- `dummy-e` has two dependencies, `dummy-c` and `dummy-d`
- `dummy-g` has just one dependency which is `dummy-c`
- etc.

Notice how `dummy-c` is a dependency of both `dummy-e` and `dummy-g`. The first time `dummy-c` appears (line 3), it's expanded fully. But then the second time it appears, the script is smart enough to know that it doesn't need to print that all out again, and can refer back to the first appearance of `dummy-c`. The same thing happens for `dummy-a`.

## Contribution wanted

For now the script ignores version numbers and version constraints. So if a dependency is there but it's not the right version, this script does not catch that issue. There is a TODO in the code where the data is available but is dropped. Please feel free to add it in and put up an MR!
