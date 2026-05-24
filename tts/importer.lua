local CONFIG = {
    source_container_guids = {
        -- "abc123",
    },
    spawn_position = { x = 0, y = 3, z = 0 },
    column_spacing = 0.6,
    row_spacing = 1.2,
    cards_per_row = 8,
    match_priority = { "card_id", "card_key", "name" },
}

function importCardReaderDeck(encoded)
    local ok, json_text = pcall(base64Decode, encoded)
    if not ok then
        error("Failed to decode base64 payload: " .. tostring(json_text))
    end

    local payload = JSON.decode(json_text)
    validatePayload(payload)

    local search_index = buildSearchIndex(CONFIG.source_container_guids)
    local requests = expandRequests(payload)
    local spawned = {}

    for index, request in ipairs(requests) do
        local source = findSourceCard(request, search_index)
        if source == nil then
            error("No source card found for '" .. tostring(request.name) .. "'.")
        end

        local spawn_position = buildSpawnPosition(index)
        local object_data = deepCopy(source.data)
        object_data.GUID = nil

        spawnObjectData({
            data = object_data,
            position = spawn_position,
            callback_function = function(spawned_object)
                applySpawnMetadata(spawned_object, request)
                table.insert(spawned, spawned_object)
            end,
        })
    end

    Wait.condition(
        function()
            finalizeImportedDeck(payload, spawned)
        end,
        function()
            return #spawned == #requests and allObjectsResting(spawned)
        end,
        15,
        function()
            print("Timed out while waiting for imported cards to finish spawning.")
        end
    )
end

function inspectCardReaderLibrary()
    local search_index = buildSearchIndex(CONFIG.source_container_guids)
    local rows = {}

    for _, entry in ipairs(search_index.entries) do
        table.insert(rows, string.format("%s | %s | %s", entry.card_id or "-", entry.card_key or "-", entry.name or "-"))
    end

    print(table.concat(rows, "\n"))
end

function validatePayload(payload)
    if type(payload) ~= "table" then
        error("Decoded payload must be a table.")
    end

    if payload.schema ~= "card-reader.tts-deck.v1" then
        error("Unsupported payload schema: " .. tostring(payload.schema))
    end

    if type(payload.deck) ~= "table" or type(payload.deck.name) ~= "string" then
        error("Payload deck metadata is invalid.")
    end

    if type(payload.cards) ~= "table" then
        error("Payload cards collection is invalid.")
    end
end

function expandRequests(payload)
    local requests = {}

    if type(payload.hero) == "table" and tonumber(payload.hero.quantity or 0) > 0 then
        for _ = 1, payload.hero.quantity do
            table.insert(requests, payload.hero)
        end
    end

    for _, entry in ipairs(payload.cards) do
        local quantity = tonumber(entry.quantity or 0) or 0
        for _ = 1, quantity do
            table.insert(requests, entry)
        end
    end

    return requests
end

function buildSearchIndex(container_guids)
    local entries = {}
    local by_card_id = {}
    local by_card_key = {}
    local by_name = {}

    for _, guid in ipairs(container_guids) do
        local container = getObjectFromGUID(guid)
        if container ~= nil then
            local data = container.getData()
            local contained_objects = data.ContainedObjects or {}

            for _, contained in ipairs(contained_objects) do
                local metadata = readSourceMetadata(contained)
                local row = {
                    data = contained,
                    card_id = metadata.card_id,
                    card_key = metadata.card_key,
                    name = metadata.name,
                }

                table.insert(entries, row)

                if row.card_id ~= nil then
                    by_card_id[normalizeLookupValue(row.card_id)] = row
                end
                if row.card_key ~= nil then
                    by_card_key[normalizeLookupValue(row.card_key)] = row
                end
                if row.name ~= nil then
                    by_name[normalizeLookupValue(row.name)] = row
                end
            end
        end
    end

    return {
        entries = entries,
        by_card_id = by_card_id,
        by_card_key = by_card_key,
        by_name = by_name,
    }
end

function readSourceMetadata(card_data)
    local gm_notes = card_data.GMNotes or ""
    local description = card_data.Description or ""
    local nickname = trim(card_data.Nickname or card_data.Name or "")
    local metadata = {
        card_id = nil,
        card_key = nil,
        name = nickname,
    }

    local parsed = decodeEmbeddedJson(gm_notes) or decodeEmbeddedJson(description)
    if parsed ~= nil then
        metadata.card_id = parsed.card_id or parsed.id
        metadata.card_key = parsed.card_key or parsed.key
        metadata.name = parsed.name or metadata.name
    end

    metadata.card_id = metadata.card_id or readTaggedLine(gm_notes, "card_reader_id") or readTaggedLine(description, "card_reader_id")
    metadata.card_key = metadata.card_key or readTaggedLine(gm_notes, "card_reader_key") or readTaggedLine(description, "card_reader_key")

    return metadata
end

function findSourceCard(request, search_index)
    for _, key in ipairs(CONFIG.match_priority) do
        local value = request[key]
        if value ~= nil and value ~= "" then
            local normalized = normalizeLookupValue(value)
            if key == "card_id" and search_index.by_card_id[normalized] ~= nil then
                return search_index.by_card_id[normalized]
            end
            if key == "card_key" and search_index.by_card_key[normalized] ~= nil then
                return search_index.by_card_key[normalized]
            end
            if key == "name" and search_index.by_name[normalized] ~= nil then
                return search_index.by_name[normalized]
            end
        end
    end

    return nil
end

function buildSpawnPosition(index)
    local zero_based = index - 1
    local column = zero_based % CONFIG.cards_per_row
    local row = math.floor(zero_based / CONFIG.cards_per_row)

    return {
        x = CONFIG.spawn_position.x + (column * CONFIG.column_spacing),
        y = CONFIG.spawn_position.y,
        z = CONFIG.spawn_position.z + (row * CONFIG.row_spacing),
    }
end

function allObjectsResting(objects)
    for _, object in ipairs(objects) do
        if object == nil or object.isDestroyed() or not object.resting then
            return false
        end
    end

    return true
end

function finalizeImportedDeck(payload, objects)
    if #objects == 0 then
        print("No cards were spawned.")
        return
    end

    local grouped = group(objects)
    local primary = grouped[1] or objects[1]

    if primary ~= nil and not primary.isDestroyed() then
        primary.setName(payload.deck.name)
        if payload.deck.description ~= nil then
            primary.setDescription(payload.deck.description)
        end
    end

    print(string.format("Imported '%s' with %d spawned cards.", payload.deck.name, #objects))
end

function applySpawnMetadata(object, request)
    if request.name ~= nil and request.name ~= "" then
        object.setName(request.name)
    end
end

function decodeEmbeddedJson(text)
    if type(text) ~= "string" or trim(text) == "" then
        return nil
    end

    local ok, parsed = pcall(JSON.decode, text)
    if ok and type(parsed) == "table" then
        return parsed
    end

    return nil
end

function readTaggedLine(text, key)
    if type(text) ~= "string" or text == "" then
        return nil
    end

    local pattern = key .. "%s*:%s*([^\r\n]+)"
    local value = string.match(text, pattern)
    if value == nil then
        return nil
    end

    return trim(value)
end

function normalizeLookupValue(value)
    return string.lower(trim(tostring(value)))
end

function trim(value)
    return (string.gsub(value, "^%s*(.-)%s*$", "%1"))
end

function deepCopy(value)
    if type(value) ~= "table" then
        return value
    end

    local result = {}
    for key, item in pairs(value) do
        result[key] = deepCopy(item)
    end
    return result
end

function base64Decode(input)
    local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    local clean = string.gsub(input, "[^" .. alphabet .. "=]", "")
    local bits = {}

    for index = 1, #clean do
        local character = string.sub(clean, index, index)
        if character ~= "=" then
            local offset = string.find(alphabet, character, 1, true)
            if offset == nil then
                error("Invalid base64 character: " .. character)
            end

            local value = offset - 1
            for shift = 5, 0, -1 do
                table.insert(bits, bit32.extract(value, shift, 1))
            end
        end
    end

    local output = {}
    for index = 1, #bits, 8 do
        if index + 7 <= #bits then
            local byte = 0
            for shift = 0, 7 do
                byte = byte + bit32.lshift(bits[index + shift], 7 - shift)
            end
            table.insert(output, string.char(byte))
        end
    end

    return table.concat(output)
end
