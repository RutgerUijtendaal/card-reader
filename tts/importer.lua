local CONFIG = {
    source_container_guids = {
        -- "abc123",
    },
    spawn_position = { x = 0, y = 3, z = 0 },
    column_spacing = 0.6,
    row_spacing = 1.2,
    cards_per_row = 8,
    fuzzy_name_distance = 1,
    index_batch_size = 50,
    spawn_batch_size = 5,
    wait_timeout_seconds = 15,
}

function importCardReaderDeck(encoded)
    local ok, json_text = pcall(base64Decode, encoded)
    if not ok then
        error("Failed to decode base64 payload: " .. tostring(json_text))
    end

    local payload = JSON.decode(json_text)
    validatePayload(payload)

    startImportJob(payload, expandRequests(payload))
end

function inspectCardReaderLibrary()
    local search_index = buildSearchIndex(CONFIG.source_container_guids)
    local rows = {}

    for _, entry in ipairs(search_index.entries) do
        table.insert(rows, entry.name or "-")
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
    local search_index = createSearchIndex()

    for _, guid in ipairs(container_guids) do
        local container = getObjectFromGUID(guid)
        if container ~= nil then
            local data = container.getData()
            local contained_objects = data.ContainedObjects or {}

            for _, contained in ipairs(contained_objects) do
                addSearchIndexEntry(search_index, contained)
            end
        end
    end

    return search_index
end

function createSearchIndex()
    return {
        entries = {},
        by_name = {},
    }
end

function addSearchIndexEntry(search_index, contained)
    local metadata = readSourceMetadata(contained)
    local row = {
        data = contained,
        name = metadata.name,
    }

    table.insert(search_index.entries, row)

    if row.name ~= nil then
        search_index.by_name[normalizeLookupValue(row.name)] = row
    end
end

function startImportJob(payload, requests)
    local job = {
        payload = payload,
        requests = requests,
        search_index = createSearchIndex(),
        source_container_guids = CONFIG.source_container_guids,
        container_index = 1,
        contained_objects = nil,
        contained_index = 1,
        request_index = 1,
        spawn_index = 1,
        expected_spawns = 0,
        spawned = {},
        missing = {},
    }

    print(string.format("Importing '%s' with %d requested cards.", payload.deck.name, #requests))
    buildSearchIndexForImport(job)
end

function buildSearchIndexForImport(job)
    local processed = 0

    while processed < CONFIG.index_batch_size do
        if job.contained_objects == nil then
            local guid = job.source_container_guids[job.container_index]
            if guid == nil then
                print(string.format("Indexed %d source cards.", #job.search_index.entries))
                spawnImportBatch(job)
                return
            end

            local container = getObjectFromGUID(guid)
            if container == nil then
                print("Source container not found: " .. tostring(guid))
                job.container_index = job.container_index + 1
            else
                local data = container.getData()
                job.contained_objects = data.ContainedObjects or {}
                job.contained_index = 1
            end
        else
            local contained = job.contained_objects[job.contained_index]
            if contained == nil then
                job.contained_objects = nil
                job.container_index = job.container_index + 1
            else
                addSearchIndexEntry(job.search_index, contained)
                job.contained_index = job.contained_index + 1
                processed = processed + 1
            end
        end
    end

    Wait.frames(function()
        buildSearchIndexForImport(job)
    end, 1)
end

function spawnImportBatch(job)
    local processed = 0

    while processed < CONFIG.spawn_batch_size do
        local request = job.requests[job.request_index]
        if request == nil then
            waitForImportSpawns(job)
            return
        end

        local source = findSourceCard(request, job.search_index)
        if source == nil then
            table.insert(job.missing, request)
        else
            local spawn_position = buildSpawnPosition(job.spawn_index)
            local object_data = deepCopy(source.data)
            object_data.GUID = nil
            job.expected_spawns = job.expected_spawns + 1
            job.spawn_index = job.spawn_index + 1

            spawnObjectData({
                data = object_data,
                position = spawn_position,
                callback_function = function(spawned_object)
                    applySpawnMetadata(spawned_object, request)
                    table.insert(job.spawned, spawned_object)
                end,
            })
        end

        job.request_index = job.request_index + 1
        processed = processed + 1
    end

    Wait.frames(function()
        spawnImportBatch(job)
    end, 1)
end

function waitForImportSpawns(job)
    logMissingCards(job.missing)

    if job.expected_spawns == 0 then
        finalizeImportedDeck(job.payload, job.spawned, job.missing)
        return
    end

    Wait.condition(
        function()
            finalizeImportedDeck(job.payload, job.spawned, job.missing)
        end,
        function()
            return #job.spawned == job.expected_spawns and allObjectsResting(job.spawned)
        end,
        CONFIG.wait_timeout_seconds,
        function()
            print(string.format(
                "Timed out while waiting for imported cards to finish spawning. Spawned %d of %d found cards.",
                #job.spawned,
                job.expected_spawns
            ))
            logMissingCards(job.missing)
        end
    )
end

function readSourceMetadata(card_data)
    local gm_notes = card_data.GMNotes or ""
    local description = card_data.Description or ""
    local nickname = trim(card_data.Nickname or card_data.Name or "")
    local metadata = {
        name = nickname,
    }

    local parsed = decodeEmbeddedJson(gm_notes) or decodeEmbeddedJson(description)
    if parsed ~= nil then
        metadata.name = parsed.name or metadata.name
    end

    return metadata
end

function findSourceCard(request, search_index)
    if request.name == nil or request.name == "" then
        return nil
    end

    local normalized = normalizeLookupValue(request.name)
    if search_index.by_name[normalized] ~= nil then
        return search_index.by_name[normalized]
    end

    return findFuzzyNameSource(normalized, search_index)
end

function findFuzzyNameSource(normalized_name, search_index)
    local match = nil
    local match_count = 0

    for _, entry in ipairs(search_index.entries) do
        if entry.name ~= nil and namesAreWithinDistance(normalized_name, normalizeLookupValue(entry.name), CONFIG.fuzzy_name_distance) then
            match = entry
            match_count = match_count + 1
            if match_count > 1 then
                return nil
            end
        end
    end

    return match
end

function namesAreWithinDistance(left, right, max_distance)
    local left_length = #left
    local right_length = #right
    local length_delta = math.abs(left_length - right_length)

    if length_delta > max_distance then
        return false
    end

    if left_length == right_length then
        local differences = 0
        for index = 1, left_length do
            if string.sub(left, index, index) ~= string.sub(right, index, index) then
                differences = differences + 1
                if differences > max_distance then
                    return false
                end
            end
        end
        return true
    end

    return namesMatchWithOneInsertionOrDeletion(left, right)
end

function namesMatchWithOneInsertionOrDeletion(left, right)
    local shorter = left
    local longer = right

    if #left > #right then
        shorter = right
        longer = left
    end

    local shorter_index = 1
    local longer_index = 1
    local skipped = 0

    while shorter_index <= #shorter and longer_index <= #longer do
        if string.sub(shorter, shorter_index, shorter_index) == string.sub(longer, longer_index, longer_index) then
            shorter_index = shorter_index + 1
            longer_index = longer_index + 1
        else
            skipped = skipped + 1
            if skipped > 1 then
                return false
            end
            longer_index = longer_index + 1
        end
    end

    return true
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

function finalizeImportedDeck(payload, objects, missing)
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

    local missing_count = #(missing or {})
    if missing_count > 0 then
        print(string.format(
            "Imported '%s' with %d spawned cards and %d missing cards.",
            payload.deck.name,
            #objects,
            missing_count
        ))
    else
        print(string.format("Imported '%s' with %d spawned cards.", payload.deck.name, #objects))
    end
end

function logMissingCards(missing)
    if missing == nil or #missing == 0 then
        return
    end

    local rows = {}
    for index, request in ipairs(missing) do
        table.insert(rows, string.format(
            "%d. %s | role=%s",
            index,
            tostring(request.name or "-"),
            tostring(request.role or "-")
        ))
    end

    print("Missing Card Reader cards:\n" .. table.concat(rows, "\n"))
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

function normalizeLookupValue(value)
    return string.lower(trim(tostring(value)))
end

function trim(value)
    if type(value) ~= "string" or value == "" then
        return ""
    end

    local first = 1
    local last = #value

    while first <= last and isWhitespace(string.sub(value, first, first)) do
        first = first + 1
    end

    while last >= first and isWhitespace(string.sub(value, last, last)) do
        last = last - 1
    end

    return string.sub(value, first, last)
end

function isWhitespace(character)
    return character == " " or character == "\t" or character == "\r" or character == "\n"
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
    local clean = cleanBase64Input(input, alphabet)
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

function cleanBase64Input(input, alphabet)
    local clean = {}

    for index = 1, #input do
        local character = string.sub(input, index, index)
        if character == "=" or string.find(alphabet, character, 1, true) ~= nil then
            table.insert(clean, character)
        end
    end

    return table.concat(clean)
end
