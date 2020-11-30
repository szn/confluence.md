# pingg

Graphical ping utility to monitor your internet connection quality.

## What it does?

`pingg` utility displays graphical (OK, ASCII style but still graphical) statistics of `ping` requests. If you have ever used `ping` as a connection quality monitor you'll got the point.

See an example. This is exact the same session (VPN to Australia followed by no connection and a full speed connection):

ping | pingg
------------ | -------------
![Plain ping](https://github.com/szn/pingg/raw/master/img/ping.png) | ![pingg example](https://github.com/szn/pingg/raw/master/img/pingg.png)

Advantages over plain `ping` are:

1. It performs a `ping` request every 5 seconds (we don't need stats every second);
2. It waits up to 5 seconds before request timeout (this is maximum reasonable request response time);
3. Response time is presented graphicaly where `1ms` is represented by empty bar and timeout is represented by a screen-wide bar of `=` signs;
4. The bar length is in a logarithmic scale to better represent observable internet connection quality.

## Installation guide

In order to 'install' `pingg` you need to place the only script available within this repository in your exacutable path. For example:

```sh
$ cd <any directory within your $PATH>
$ wget https://github.com/szn/pingg/raw/master/pingg
$ chmod 755 pingg
```

`pingg` uses external utilities such as, `dig`, `grep`, `wc`, `tput`, `ping`, `cut`, `bc`, `printf` and `seq`. All of them should be available in any mordern unix-alike operating system.

## How to use

Using `pingg` is as simple as typing the script name in your terminal window:

```sh
$ pingg
IP address 8.8.8.8
   499ms ====================
    30ms
```

`pingg` uses Google DNS server IP address by default (`8.8.8.8`). You could change that providing either an IP address or host name as the first parameter. Examples are:

```sh
$ pingg 8.8.4.4
$ pingg nieradka.net
```
