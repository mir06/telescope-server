# Init scripts

Here you will find Systemd and System V initscripts to run the
telescope-server automatically.

## Systemd

Replace `@BINDIR@` by the location of the installed `telescope-server`
script (e.g. `$VIRTUAL_ENV/bin`) and copy it to `/etc/systemd/system/`

```shell
bindir=$(dirname $(which telescope-server))
sed "s#@BINDIR@#$bindir#g" telescoped.service.in > /etc/systemd/system/telescoped.service
```
and activate it
```shell
systemctl enable telescoped
systemctl start telescoped
```

## System V

For SysV-based systems copy and adapt `telescoped.sysv.in` to
`/etc/init.d/telescoped`

```shell
bindir=$(dirname $(which telescope-server))
sed "s#@BINDIR@#$bindir#g" telescoped.sysv.in > /etc/init.d/telescoped
```
and activate it
```
chmod 755 /etc/init.d/telescoped
update-rc.d telescoped defaults
/etc/init.d/telescoped start
```

## Defaults
If you want or need to change default settings copy `telescoped.default` to
`/etc/default/telescoped` and edit that file.
