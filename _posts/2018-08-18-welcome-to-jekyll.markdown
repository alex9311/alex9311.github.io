---
layout: post
title:  "Trying out Jekyll"
date:   2018-08-18 22:40:29 -0700
categories: jekyll software
---

This weekend I'm trying out GitHub Pages with Jekyll to host a static site.
[Jekyll](https://jekyllrb.com/) is a static website generator built on Ruby.
What really interested me is how you can get free hosting for Jekyll sites on GitHub Pages. 

There are a lot of existing guides about this topic, so I won't bother to write a detailed one.
Here is a simplified version of the steps I followed to get going with Jekyll on GitHub Pages.

- installed Ruby and Jekyll
- generated a Jekyll site and pushed it to my GitHub Pages [repo](https://github.com/alex9311/alex9311.github.io)
- used [Namecheap](https://www.namecheap.com/) to register alexandersimes.com ($8 for a year)
- set the Host Records in Namecheap to point to my GitHub Pages domain ([tutorial](https://www.namecheap.com/support/knowledgebase/article.aspx/9645/2208/how-do-i-link-my-domain-to-github-pages))
- set GitHub Pages up with a custom domain ([tutorial](https://help.github.com/articles/using-a-custom-domain-with-github-pages/))

Thats all!
Took about 30 minutes to get it all working plus a bit of wait time for the DNS server to update.

So far, I am very impressed.
Being able to test locally with a quick `jekyll serve` from a copy of my repo is great.
Further, simply pushing to `master` on my repo triggers a build which updates my live site.
I'm planinng to spend some time looking at open source templates and integrating Google Analytics.

![jekyll-hide](https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Dr_Jekyll_and_Mr_Hyde_poster_edit2.jpg/1024px-Dr_Jekyll_and_Mr_Hyde_poster_edit2.jpg)
