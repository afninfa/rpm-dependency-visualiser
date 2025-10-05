# rpm-dependency-visualiser

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

There are probably a bunch of dependency relationships here. For example in my case
- `dummy-f` has two dependencies, `dummy-e` and `dummy-g`
- `dummy-e` has two dependencies, `dummy-c` and `dummy-d`
- `dummy-g` has just one dependency which is `dummy-c`
- `dummy-c` has two dependencies, `dummy-a` and `dummy-b`
- Finally, `dummy-b` also depends on `dummy-a`

`rpmdag.py` shows you the DAG structure in text form

```
$ python3 rpmdag.py . dummy-f-1.3-1.x86_64.rpm
0001: └─ dummy-f
0002:    ├─ dummy-e
0003:    │  ├─ dummy-c
0004:    │  │  ├─ dummy-a (no dependencies)
0005:    │  │  └─ dummy-b
0006:    │  │     └─ dummy-a (see line 4)
0007:    │  └─ dummy-d (no dependencies)
0008:    └─ dummy-g
0009:       └─ dummy-c (see line 3)
```

## Contribution wanted

For now the script ignores version numbers and version constraints. So if a dependency is there but it's not the right version, this script does not catch that issue. There is a TODO in the code where the data is available but is dropped. Please feel free to add it in and put up an MR!
