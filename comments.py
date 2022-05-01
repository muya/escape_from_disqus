import sh
import os
import json
import dateutil.parser as parser
from markdownify import markdownify as md

import xml.dom.minidom

def get_ancestry(ancestors, k):
  a = child_ancestry[k]
  if a != "":
    ancestors.insert(0, a.zfill(12))
    get_ancestry(ancestors, a)

doc = xml.dom.minidom.parse("comments.xml")

articles = {}

# Collect articles
for article in doc.getElementsByTagName("thread"):
  id = article.getAttribute("dsq:id").strip()

  try:
    link = article.getElementsByTagName("link")[0].firstChild.nodeValue.strip()
  except IndexError:
    continue

  # don't know why some articles have a query string.
  if "?" in link:
    link = link.split("?")[0]

  # 1970/ is my drafts folder; localhost:4000 is my local endpoint for the blog
  if "/1970/" in link or "web.archive.org/" in link or "http://localhost:4000" in link:
    continue

  # Normalize the http and https prefixed IDs
  if "https://blog.muya.co.ke" in link or "http://blog.muya.co.ke" in link:
    link = link.replace("http://blog.muya.co.ke","").replace("https://blog.muya.co.ke", "")
    if id not in articles:
        articles[id] = { "link": link}

print("finished collecting articles. found %d" % len(articles))

child_ancestry = {}

# Collect Comments
for post in doc.getElementsByTagName("post"):

  article = post.getElementsByTagName("thread")[0].getAttribute("dsq:id").strip()

  print("processing article %s" % article)

  if article in articles:

    if "true" in "" + post.getElementsByTagName("isSpam")[0].firstChild.nodeValue:
        print("article %s is spam" % article)
        continue
    if "true" in "" + post.getElementsByTagName("isDeleted")[0].firstChild.nodeValue:
        print("article %s is deleted" % article)
        continue

    parent = post.getElementsByTagName("parent")
    if len(parent) > 0:
        parent = parent[0].getAttribute("dsq:id")
    else:
        parent = ""

    postId = post.getAttribute("dsq:id")

    child_ancestry[postId] = parent

    if "posts" not in articles[article]:
      articles[article]["posts"] = {}

    articles[article]["posts"][postId] = {
      "createdAt": parser.parse(post.getElementsByTagName("createdAt")[0].firstChild.nodeValue).strftime("%Y-%m-%d %H:%M:%S"),
      "who": post.getElementsByTagName("name")[0].firstChild.nodeValue,
      "message": post.getElementsByTagName("message")[0].firstChild.nodeValue
    }

articles_with_comments = {}

# Only articles with comments
for article_key, article in articles.items():
  if "posts" in article:
    articles_with_comments[article_key] = article

print("found %d articles with comments" % len(articles_with_comments))

for article_key, article in articles_with_comments.items():
  for post_article_key, post in articles_with_comments[article_key]["posts"].items():
    if "posts" not in articles_with_comments[article_key]:
      articles_with_comments[article_key]["posts"] = {}
    articles_with_comments[article_key]["posts"][post_article_key] = post
    ancestors = []
    ancestors.insert(0, post_article_key.zfill(12))
    get_ancestry(ancestors, post_article_key)

    articles_with_comments[article_key]["posts"][post_article_key]["order"] = ",".join(ancestors)
    articles_with_comments[article_key]["posts"][post_article_key]["indent"] = len(ancestors) -1

# Change posts from a dict to a list
for article_key, article in articles_with_comments.items():
  article["posts"] = article["posts"].values()

# Actual JSON output.
for article_key, article in articles_with_comments.items():
  if not os.path.exists("disqusoutput"):
    os.makedirs("disqusoutput")
  file = open("disqusoutput/" + article["link"].replace("/","-").replace(".","-") + ".json", "w")
  file.write(json.dumps(list(article["posts"]), indent=4, sort_keys=True))
  file.close()

# Actual HTML output.
for article_key, article in articles_with_comments.items():
  file = open("disqusoutput/" + article["link"].replace("/", "-").replace(".","-") + ".html", "w")
  file.writelines("<h2>Comments formerly in Disqus, but exported and mounted statically ...</h2><br/>")
  file.writelines("<table class='table table-striped'>\n")
  for post in sorted(article["posts"], key=lambda x: x['order']):
    w = str(50 * post["indent"])
    file.writelines("<tr><td style='padding-left: " + w + "px' class='dTS'>" + post["createdAt"] + "</td><td class='dU'>" + post["who"] + "</td></tr>\n")
    file.writelines("<tr><td style='padding-left: " + w + "px' colspan='2' class='dMessage'>" + post["message"] + "</td></tr>\n")
  file.writelines("</table>\n")
  file.close()


# Markdown output
for article_key, article in articles_with_comments.items():
  file = open("disqusoutput/" + article["link"].replace("/", "-").replace(".","-") + ".md", "w")
  file.writelines("## Comments Previously on Disqus")
  file.writelines("\n\n")
  for post in sorted(article["posts"], key=lambda x: x['order']):

    blockquote_indents = (">" * (post["indent"] + 1)) + " "

    file.writelines(blockquote_indents + "_Originally by: **" + post["who"] + "** on **" + post["createdAt"] + "**_ \n")

    # parse html from message, and convert to markdown
    h = md(post["message"], newline_style="SPACES")

    adjusted_msg = h.replace("\n", "\n"+blockquote_indents)

    file.writelines(adjusted_msg)

    file.writelines("\n\n")

  file.writelines("\n\n\n")
  file.close()
