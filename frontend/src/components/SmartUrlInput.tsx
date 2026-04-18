import { useState } from "react";
import {
  ActionIcon,
  Menu,
  TextInput,
} from "@mantine/core";
import {
  IconBrain,
  IconDownload,
  IconMovie,
  IconPhoto,
  IconSearch,
  IconSitemap,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";

const MEDIA_HOSTS = [
  "youtube.com", "youtu.be", "instagram.com", "tiktok.com",
  "twitter.com", "x.com", "facebook.com", "vimeo.com",
  "reddit.com", "pinterest.com", "twitch.tv", "soundcloud.com",
];

function detectType(url: string): "media" | "web" | null {
  if (!url.trim()) return null;
  try {
    const host = new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace("www.", "");
    if (MEDIA_HOSTS.some((h) => host === h || host.endsWith(`.${h}`))) return "media";
  } catch {}
  return "web";
}

export default function SmartUrlInput() {
  const [url, setUrl] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const nav = useNavigate();

  const goTo = (route: string, urlParam: string) => {
    nav(`${route}?url=${encodeURIComponent(urlParam)}`);
    setUrl("");
    setMenuOpen(false);
  };

  const onSubmit = () => {
    if (!url.trim()) return;
    const type = detectType(url);
    if (type === "media") {
      goTo("/media", url);
    } else {
      setMenuOpen(true);
    }
  };

  return (
    <Menu opened={menuOpen} onChange={setMenuOpen} shadow="md" width={240}>
      <Menu.Target>
        <TextInput
          size="xs"
          placeholder="Paste URL - auto-detect tool"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSubmit();
          }}
          rightSection={
            <ActionIcon variant="subtle" size="sm" onClick={onSubmit} aria-label="Search URL">
              <IconSearch size={14} />
            </ActionIcon>
          }
          w={{ base: 180, sm: 300 }}
          styles={{ input: { fontSize: 12 } }}
        />
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>Open with…</Menu.Label>
        <Menu.Item leftSection={<IconPhoto size={14} />} onClick={() => goTo("/harvester", url)}>
          Image Harvester
        </Menu.Item>
        <Menu.Item leftSection={<IconSitemap size={14} />} onClick={() => goTo("/mapper", url)}>
          URL Mapper
        </Menu.Item>
        <Menu.Item leftSection={<IconDownload size={14} />} onClick={() => goTo("/ripper", url)}>
          Site Ripper
        </Menu.Item>
        <Menu.Item leftSection={<IconMovie size={14} />} onClick={() => goTo("/media", url)}>
          Media Downloader
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
