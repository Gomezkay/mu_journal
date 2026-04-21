from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Article


class LatestArticlesFeed(Feed):
    title = "MUMJ Latest Articles"
    link = "/rss/"
    description = "Latest articles published in the Mulungushi University Multidisciplinary Journal."

    def items(self):
        return Article.objects.filter(is_active=True)[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.abstract or item.citation_text

    def item_link(self, item):
        return reverse("volume-detail", args=[item.volume.slug])
