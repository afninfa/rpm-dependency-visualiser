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
$ python3 rpmdag.py x86_64 x86_64/dummy-f-1.3-1.x86_64.rpm
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

You don't have to specify a root RPM. If you don't, it will expand everything in the provided
directory in a random order.

```
$ python3 rpmdag.py x86_64
0001: └─ dummy-g
0002:    └─ dummy-c
0003:       ├─ dummy-a (no dependencies)
0004:       └─ dummy-b
0005:          └─ dummy-a (see line 3)
0006:
0007: └─ dummy-c (see line 2)
0008:
0009: └─ dummy-f
0010:    ├─ dummy-e
0011:    │  ├─ dummy-c (see line 2)
0012:    │  └─ dummy-d (no dependencies)
0013:    └─ dummy-g (see line 1)
0014:
0015: └─ dummy-b (see line 4)
0016:
0017: └─ dummy-a (see line 3)
0018:
0019: └─ dummy-e (see line 10)
0020:
0021: └─ dummy-d (see line 12)
0022:
```

## Version number checking (WIP)

I created another rpm `dummy-h` which requires `dummy-c` and `dummy-f` but versions which don't
match the ones I have. The program doesn't crash, it still builds the tree, it just warns
you at the bottom like this

```
$ python3 rpmdag.py x86_64 x86_64/dummy-h-1.3-1.x86_64.rpm
0001: └─ dummy-h
0002:    ├─ dummy-c
0003:    │  ├─ dummy-a (no dependencies)
0004:    │  └─ dummy-b
0005:    │     └─ dummy-a (see line 3)
0006:    └─ dummy-f
0007:       ├─ dummy-e
0008:       │  ├─ dummy-c (see line 2)
0009:       │  └─ dummy-d (no dependencies)
0010:       └─ dummy-g
0011:          └─ dummy-c (see line 2)
Warning: dummy-h requires dummy-c version = 0.9 but the local copy is version 1.0-1.
Warning: dummy-h requires dummy-f version >= 1.5 but the local copy is version 1.3-1.
```

Please note this feature is not very widely tested and it probably will not give correct outputs
in more serious settings. This is a work in progress.