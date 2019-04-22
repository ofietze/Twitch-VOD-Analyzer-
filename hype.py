import operator
import argparse
import datetime
import os
import re
import sys
import twitch
from subprocess import call
try:
    import httplib
except:
    import http.client as httplib

def parseFile(keywords, path, limit):
    try:
        open(path)

    except FileNotFoundError:
        sys.stderr.write("Error: " + path + " does not exist!")
        sys.exit(1)

    # filter only if custom keywords were set, 1 is standard (TotalWords)
    filterKeywords = len(keywords) > 1
    with open(path) as f:
        lines = [line.rstrip('\n') for line in f]
        for line in lines:
            keywords = parseLine(keywords, line.lower(), filterKeywords)
    f.close()
    return keywords

def parseLine(keywords, line, filterKeywords):
    # Get only the text, cut timestamp and user names
    for word in line.split():
        keywords["TotalWords"] += 1
        if word in keywords:
            keywords[word] += 1
        else:
            if filterKeywords == False:
                keywords[word] = 1

    return keywords



# returns filepath to chat log file
def getChatForURL(url, internetOn, helix):
    # Gets the ID of the VOD (9-digit number) from the url
    id = url.split("/")[4][0:9]

    # check whether system is online or offline
    if internetOn == True:
        print("twitch.tv reachable")
        print(helix.video(id).title)
        # check if already downloaded
        path = "log/" + id + ".log"
        try:
            open(path)
            print("Chat log already downloaded")

        except FileNotFoundError:
            downloadChatLog(id, helix)
    else:
        print("twitch.tv unreachable")
        # check if already downloaded
        path = "log/" + id + ".log"
        try:
            open(path)
            print("Chat log already downloaded")

        except FileNotFoundError:
            print("Chat log not downloaded and no active internet connection available")
            sys.exit(1)
    return path

def internetOn():
    conn = httplib.HTTPConnection("www.twitch.tv", timeout=3)
    try:
        conn.request("HEAD", "/")
        conn.close()
        return True
    except:
        conn.close()
        return False

def downloadChatLog(id, helix):
    savePath = os.path.dirname(os.path.abspath(__file__)) + "/log/"+id+".log"
    print("Downloading chat log to " + savePath)
    count = 0
    with open("log/"+id +'.log', 'w') as f:
        for comment in helix.video(id).comments():
            count += 1
            if count % 100 == 0:
                print(str(count) + " messages received\r", end="")
            f.write(comment.message.body+ " ")
    f.close()


def saveStats(keywords, limit, helix, id, url, internetOn):
    # only display top <limit> most frequent words
    if len(keywords) == 0:
        print("No occurences of given words found")
        return

    topKeywords = (sorted(keywords.items(), key = operator.itemgetter(1)))[::-1]
    topWords = []
    topValues = []
    totalWords = float(keywords["TotalWords"])
    if internetOn == True:
        filename = helix.video(id).title.replace(" ", "")
    else:
        filename = id

    with open("results/" + filename +'.txt', 'w') as f:
        views = 1
        duration = 1
        if internetOn == True:
            video = helix.video(id)
            f.write(video.title+"\n")
            # Parse video duration
            regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
            parts = regex.match(video.duration).groupdict()

            timeParams = {}
            for name, param in parts.items():
                if param:
                    timeParams[name] = int(param)

            videoDuration = datetime.timedelta(**timeParams)
            f.write("Duration: "+str(videoDuration)+"\n")
            f.write("Views: " + str(video.view_count) + "\n")
            duration = videoDuration.seconds/60
        f.write(url+"\n")
        f.write(str(keywords["TotalWords"]) + " words total\n")

        if len(topKeywords) < limit:
            limit = len(topKeywords)

        f.write("\n<<top " + str(limit-1)+">>\n")

        hypewords = ["pogchamp", "dps", "pog"]
        badwords = ["goats", "residentsleeper"]
        hype = 0
        # hypescore is in percent with 100% beeing the most hype
        for i in range(1, len(topKeywords)):
            topWords.append(topKeywords[i][0])
            topValues.append(topKeywords[i][1])
            # print "word: #occurences (percentage)
            percentage = round(topKeywords[i][1]/totalWords * 100, 2)
            per10Min = round(topKeywords[i][1]/float(duration))
            if i < limit:
                f.write('{:<30}{:<30}{:<}'.format(topKeywords[i][0]+": "+ str(topKeywords[i][1]),
                    "("+ str(percentage) +"%)", str(per10Min) + " per 10 minutes\n"))

            # hype/bad words affect score  hype +/-= i * percentage/2
            if topWords[i-1] in hypewords:
                hype += percentage * 3
            if topWords[i-1] in badwords:
                hype -= percentage * 3

        f.write("\n<<"+str(round(hype, 1)) + " hypescore>>\n")
        print("\n<<"+str(round(hype, 1)) + " hypescore>>")
        if hype <= 10:
            f.write("Boring match. Don't waste your time, skip this one\n")
            print("Boring match. Don't waste your time, skip this one")
        else:
            if hype >= 15:
                f.write("Hype match. Go watch it right now!\n")
                print("Hype match. Go watch it right now!")
            else:
                f.write("Nice match. Watch it if you want\n")
                print("Nice match. Watch it if you want")
        for word in hypewords:
            percentage = round(keywords[word]/totalWords * 100, 2)
            f.write('{:<30}{:<30}{:<}'.format(word + ":"+ str(keywords[word]),"("+str(percentage)+"%)", "+"+ str(round(3*percentage, 2))+"\n"))
        f.write("\n")
        for word in badwords:
            percentage = round(keywords[word]/totalWords * 100, 2)
            f.write('{:<30}{:<30}{:<}'.format(word + ":"+ str(keywords[word]),"("+str(percentage)+"%)", "-"+ str(round(3*percentage, 2))+"\n"))
    f.close()
    print("See output file for more details")
    print("Wrote results to results/" + filename +".txt")

def main():
    helix = twitch.Helix('5sjjv1h9pkl1vpdt6eojmjkbgfzycg')

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-u', '--url',help='url of Twitch-VOD to download chat for', required=True)
    parser.add_argument('-n','--number',help='Most frequent n words will be shown', required=False, default=20, type=int)
    parser.add_argument('-s','--save',help='Whether results shoud be written to a text file (y/n)', required=False, default="n")

    args = parser.parse_args()

    keywords = {}

    limit = args.number + 1
    # adding word counter to keywords dictionary, no collision with real keywords,
    # because they are converted to lower case
    keywords["TotalWords"] = 0
    path = getChatForURL(args.url, internetOn(), helix)
    keywords = parseFile(keywords, path, limit)
    saveStats(keywords, limit, helix, path[4:13], args.url, internetOn())

if __name__ == '__main__':
    main()
