# Upranker: an osu! tournament utilities Discord bot
### currently, the main (and only) feature of upranker is self-scheduling
players and hosts know how inconvenient the process of manual scheduling is:

1. ask opponent for reschedule
2. screenshot their approval
3. send in reschedule channel
4. wait for staff to approve
5. staff manually edits spreadsheet with new time

### upranker aims to ease this process using the python module [gspread](https://docs.gspread.org/en/latest/)

---

### here's a usage example from the tournament [regression rumble](https://osu.ppy.sh/community/forums/topics/1789703?n=1):

command syntax

![example command: reschedule](https://imgur.com/Nqd3qu3.png)

spreadsheet (before)

![reschedule before spreadsheet](https://imgur.com/TJ4h7VS.png)

sending the reschedule request (dates in brackets are shown to the user in their local time)

![example command usage: reschedule](https://imgur.com/j49tXb8.png)

accepting the reschedule request (they sent a new request for a different time)

![example command usage: reschedule accept](https://imgur.com/DtbZehs.png)

spreadsheet (after)

![reschedule after spreadsheet](https://imgur.com/SdVFX8I.png)

if there is a ref for the match, they are pinged as well

![reschedule accept ref ping](https://imgur.com/FfKIabd.png)

---

### usage example for qualifiers:

command syntax

![example command: qualifier](https://imgur.com/P3qD8jy.png)

sending the command

![example command usage: qualifier](https://imgur.com/mXRpjPS.png)

result on spreadsheet (the second team later rescheduled to a different lobby)

![spreadsheet result for qualifier](https://imgur.com/IB9fIPW.png)

---

### wanna use this bot for your upcoming tournament?

upranker is still very early in development and is not yet ready for fully public use, so i am currently only allowing for one tournament at a time. contact me on discord ``@tranq_``; first come first serve. expect bugs to occur and expect to have to use a certain ref sheet for your tournament

---

### acknowledgements

- special thanks to megumic (host of regression rumble) for pitching me the self-scheduling idea
- special thanks to shdewz; they originally made a bot with similar functionality which i took inspiration from
- special thanks to everyone in the screenshots above
